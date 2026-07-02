// Render templates for blog-craft.
//
// Modes:
//   render-template --src <dir> --dst <dir> --answers <yaml>
//      One-pass mode. Walk --src; for each file, render *.tmpl through
//      text/template (writing to corresponding path under --dst, sans .tmpl)
//      or copy verbatim. Top-level keys of <yaml> become template root context.
//
//   render-template --src <dir> --dst <dir> --answers <yaml> --per-series
//      Per-series mode. The same walk runs once per series in answers.series.
//      Inside each iteration:
//        - .this    is the current series object (key, title, description, weight)
//        - .today   is YYYY-MM-DD
//        - all other top-level keys from <yaml> are also available
//      Output goes to <dst>/<series.key>/<rest-of-path>.
//
// Funcs registered: add, indent, quote, toYaml, default.
package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"text/template"
	"time"

	"gopkg.in/yaml.v3"
)

func main() {
	src := flag.String("src", "", "Source template directory (required for render modes)")
	dst := flag.String("dst", "", "Destination directory (required for render modes)")
	answers := flag.String("answers", "", "Path to wizard-answers YAML (required)")
	perSeries := flag.Bool("per-series", false, "Render src once per series, output to <dst>/<series.key>/")
	checkOnly := flag.Bool("check", false, "Just parse --answers and exit 0/1; no rendering")
	getBool := flag.String("get-bool", "", "Print 'true'/'false' for the dotted key (e.g. features.series_overview_posts) and exit")
	has := flag.String("has", "", "Exit 0 if the dotted key exists and is non-nil, else 1")
	flag.Parse()

	if *answers == "" {
		fmt.Fprintln(os.Stderr, "usage: render-template --answers <yaml> [render flags] | [--check] | [--get-bool <key>]")
		os.Exit(2)
	}

	data, err := loadAnswers(*answers)
	if err != nil {
		log.Fatalf("load answers: %v", err)
	}

	if *checkOnly {
		// loadAnswers already parsed it.
		return
	}

	if *getBool != "" {
		v, ok := digBool(data, strings.Split(*getBool, "."))
		if !ok {
			fmt.Fprintf(os.Stderr, "key %q not found or not a bool\n", *getBool)
			os.Exit(1)
		}
		fmt.Println(v)
		return
	}

	if *has != "" {
		v, ok := dig(data, strings.Split(*has, "."))
		if ok && v != nil {
			return
		}
		os.Exit(1)
	}

	if *src == "" || *dst == "" {
		fmt.Fprintln(os.Stderr, "render mode requires --src and --dst")
		os.Exit(2)
	}

	if !*perSeries {
		if err := walkAndRender(*src, *dst, data); err != nil {
			log.Fatalf("render: %v", err)
		}
		return
	}

	series, ok := data["series"].([]interface{})
	if !ok || len(series) == 0 {
		log.Fatalf("--per-series: data.series is missing or empty")
	}
	for i, raw := range series {
		s, ok := raw.(map[string]interface{})
		if !ok {
			log.Fatalf("--per-series: series[%d] is not a mapping", i)
		}
		s["weight"] = i + 1
		key, _ := s["key"].(string)
		if key == "" {
			log.Fatalf("--per-series: series[%d].key is missing", i)
		}
		ctx := map[string]interface{}{}
		for k, v := range data {
			ctx[k] = v
		}
		ctx["this"] = s
		ctx["today"] = time.Now().UTC().Format("2006-01-02")
		seriesDst := filepath.Join(*dst, key)
		if err := walkAndRender(*src, seriesDst, ctx); err != nil {
			log.Fatalf("render series %s: %v", key, err)
		}
	}
}

func loadAnswers(path string) (map[string]interface{}, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m map[string]interface{}
	if err := yaml.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	return m, nil
}

func walkAndRender(src, dst string, data map[string]interface{}) error {
	src = filepath.Clean(src)
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		outRel := strings.TrimSuffix(rel, ".tmpl")
		out := filepath.Join(dst, outRel)
		if err := os.MkdirAll(filepath.Dir(out), 0o755); err != nil {
			return err
		}
		if strings.HasSuffix(rel, ".tmpl") {
			return renderFile(path, out, data)
		}
		return copyFile(path, out)
	})
}

func renderFile(in, out string, data map[string]interface{}) error {
	src, err := os.ReadFile(in)
	if err != nil {
		return err
	}
	tmpl, err := template.New(filepath.Base(in)).Funcs(funcs()).Parse(string(src))
	if err != nil {
		return fmt.Errorf("parse %s: %w", in, err)
	}
	f, err := os.Create(out)
	if err != nil {
		return err
	}
	defer f.Close()
	if err := tmpl.Execute(f, data); err != nil {
		return fmt.Errorf("execute %s: %w", in, err)
	}
	return nil
}

func copyFile(in, out string) error {
	srcF, err := os.Open(in)
	if err != nil {
		return err
	}
	defer srcF.Close()
	dstF, err := os.Create(out)
	if err != nil {
		return err
	}
	defer dstF.Close()
	if _, err := io.Copy(dstF, srcF); err != nil {
		return err
	}
	srcInfo, err := os.Stat(in)
	if err == nil {
		_ = os.Chmod(out, srcInfo.Mode())
	}
	return nil
}

func digBool(m map[string]interface{}, path []string) (bool, bool) {
	var cur interface{} = m
	for _, p := range path {
		mm, ok := cur.(map[string]interface{})
		if !ok {
			return false, false
		}
		cur, ok = mm[p]
		if !ok {
			return false, false
		}
	}
	b, ok := cur.(bool)
	return b, ok
}

// dig walks a dotted path, returning the value and whether it resolved.
func dig(m map[string]interface{}, path []string) (interface{}, bool) {
	var cur interface{} = m
	for _, p := range path {
		mm, ok := cur.(map[string]interface{})
		if !ok {
			return nil, false
		}
		cur, ok = mm[p]
		if !ok {
			return nil, false
		}
	}
	return cur, true
}

func funcs() template.FuncMap {
	return template.FuncMap{
		"add": func(a, b int) int { return a + b },
		"indent": func(n int, s string) string {
			pad := strings.Repeat(" ", n)
			lines := strings.Split(s, "\n")
			for i, line := range lines {
				lines[i] = pad + line
			}
			return strings.Join(lines, "\n")
		},
		"quote": func(s string) string {
			return strconv.Quote(s)
		},
		// toYaml marshals an arbitrary value to YAML (used to pass structured v2
		// config blocks — image.layers, content_types, features — through verbatim).
		"toYaml": func(v interface{}) string {
			out, err := yaml.Marshal(v)
			if err != nil {
				return fmt.Sprintf("# toYaml error: %v", err)
			}
			return strings.TrimRight(string(out), "\n")
		},
		// default returns def when val is nil or an empty string (config
		// palette tokens with fallbacks). Usage: {{ default "#fff" .x }}
		"default": func(def, val interface{}) interface{} {
			if val == nil || val == "" {
				return def
			}
			return val
		},
	}
}
