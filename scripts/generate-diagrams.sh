#!/bin/bash
# Generate PNG images from PlantUML diagrams
# Requires: plantuml (apt install plantuml or brew install plantuml)
# Or: java -jar plantuml.jar

echo "Generating PNGs from PUML diagrams..."

for puml in docs/diagramas/*.puml; do
    name=$(basename "$puml" .puml)
    if command -v plantuml &>/dev/null; then
        plantuml -tpng "$puml" -o png/
        echo "✓ $name.png"
    else
        echo "⚠ plantuml not installed. Install: apt install plantuml"
        echo "  Then run: plantuml -tpng docs/diagramas/*.puml"
        exit 1
    fi
done

echo "Done! PNGs in docs/diagramas/png/"
