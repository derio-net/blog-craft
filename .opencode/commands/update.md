---
description: Non-destructively update an existing blog-craft blog to the latest blog-craft.
  Migrates the config up the schema ladder, re-renders to staging, and 3-way-merges
  shipped changes into the blog — surfacing conflicts, never clobbering operator edits.
  Use when pulling a newer blog-craft into a blog, or when .blog-craft.yaml is behind
  the current schema version.
---
Use the `update` skill to handle this request.

$ARGUMENTS
