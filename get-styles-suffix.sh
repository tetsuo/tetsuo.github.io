#!/usr/bin/env bash

shopt -s globstar nullglob
files=(scss/**/*.scss scss/**/*.css)
sorted_files=($(printf "%s\n" "${files[@]}" | sort))
cat styles.scss "${sorted_files[@]}" 2>/dev/null | sha1sum | cut -c1-4