#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 <file_extension> <days>"
    echo "Example: $0 log 30"
    exit 1
fi

file_ext=$1
days=$2

if ! [[ "$days" =~ ^[0-9]+$ ]]; then
    echo "Error: Days must be a positive integer"
    exit 1
fi

find . -name "*.$file_ext" -type f -mtime +$days -exec rm -f {} \;

echo "Removed all .$file_ext files older than $days days"
