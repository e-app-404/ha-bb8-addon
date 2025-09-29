#!/bin/bash
# Cross-Repository ADR Link Validation Script
# See ADR-0030 for specification

set -e

echo "🔗 Validating cross-repository ADR links..."

# Configuration
ADR_DIR="docs/ADR"
TIMEOUT=10
ERRORS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
NC='\033[0m' # No Color

validate_url() {
    local url="$1"
    local context="$2"
    
    echo -n "  Checking: $(basename "$url")... "
    
    # Use curl with timeout and follow redirects
    if curl -f -s --max-time "$TIMEOUT" --head "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        echo -e "    ${RED}BROKEN:${NC} $url"
        echo -e "    ${YELLOW}Context:${NC} $context"
        return 1
    fi
}

# Extract and validate GitHub URLs from ADR files
echo "📄 Scanning ADR files for external references..."

if [ ! -d "$ADR_DIR" ]; then
    echo -e "${RED}Error:${NC} ADR directory not found: $ADR_DIR"
    exit 1
fi

# Find all ADR markdown files
adr_files=$(find "$ADR_DIR" -name "ADR-*.md" -type f)

if [ -z "$adr_files" ]; then
    echo -e "${YELLOW}Warning:${NC} No ADR files found in $ADR_DIR"
    exit 0
fi

echo "Found $(echo "$adr_files" | wc -l) ADR files"

# Extract URLs from front-matter and content
for adr_file in $adr_files; do
    echo "📋 Processing: $(basename "$adr_file")"
    
    # Extract URLs from external_related YAML blocks  
    external_urls=$(grep -A 20 "external_related:" "$adr_file" | grep -E "^\s*url:" | sed 's/.*url:\s*["\x27]*//' | sed 's/["\x27]*$//' | grep -E "^https?://")
    
    # Extract GitHub URLs from markdown links
    github_urls=$(grep -oE "https://github\.com/[^)]*docs/ADR/[^)]*\.md" "$adr_file" || true)
    
    # Combine all URLs
    all_urls=$(echo -e "$external_urls\n$github_urls" | grep -v "^$" | sort -u)
    
    if [ -n "$all_urls" ]; then
        echo "  Found $(echo "$all_urls" | wc -l) external reference(s)"
        
        while IFS= read -r url; do
            if [ -n "$url" ]; then
                if ! validate_url "$url" "$(basename "$adr_file")"; then
                    ((ERRORS++))
                fi
            fi
        done <<< "$all_urls"
    else
        echo -e "  ${YELLOW}No external references found${NC}"
    fi
    
    echo ""
done

# Summary
echo "🏁 Validation Summary:"
echo "  Total errors: $ERRORS"

if [ $ERRORS -eq 0 ]; then
    echo -e "  ${GREEN}✅ All cross-repository links are valid!${NC}"
    exit 0
else
    echo -e "  ${RED}❌ Found $ERRORS broken cross-repository link(s)${NC}"
    echo ""
    echo "💡 Next steps:"
    echo "  1. Verify the target repositories are accessible"
    echo "  2. Check if ADR files have been moved or renamed"
    echo "  3. Update URLs in ADR front-matter and content"
    echo "  4. Consider using commit SHAs for immutable references"
    exit 1
fi