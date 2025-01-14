#!/bin/bash

# Function to convert bytes to human readable format
function hr_size() {
    awk 'function hr(bytes) {
        hum[1024^4]="TiB";
        hum[1024^3]="GiB";
        hum[1024^2]="MiB";
        hum[1024]="KiB";
        for (x = 1024^4; x >= 1024; x /= 1024) {
            if (bytes >= x) {
                return sprintf("%.2f %s", bytes/x, hum[x]);
            }
        }
        return sprintf("%d B", bytes);
    }
    {print hr($1)}'
}

# Get ARC stats
arc_stats=$(cat /proc/spl/kstat/zfs/arcstats)

# Extract key values
current=$(echo "$arc_stats" | awk '/^size/ {print $3}')
target=$(echo "$arc_stats" | awk '/^c/ {print $3}')
max=$(echo "$arc_stats" | awk '/^c_max/ {print $3}')
hits=$(echo "$arc_stats" | awk '/^hits/ {print $3}')
misses=$(echo "$arc_stats" | awk '/^misses/ {print $3}')

# Calculate hit ratio
total=$((hits + misses))
ratio=$(awk "BEGIN {printf \"%.2f\", $hits/$total*100}")

# Display results
echo "ARC Usage Summary:"
echo "Current size: $(echo $current | hr_size)"
echo "Target size:  $(echo $target | hr_size)"
echo "Maximum size: $(echo $max | hr_size)"
echo "Hit ratio:    ${ratio}%"
