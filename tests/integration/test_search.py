import json
import os

import pytest
from thefuzz import process


# Implement the search_illustrations function directly in the test script
def search_illustrations(search_term: str):
    try:
        # Adjust the path to work from the tests/integration directory
        illustrations_path = os.path.join("..", "..", "backend", "knowledge", "illustrations.json")
        with open(illustrations_path, "r") as f:
            illustrations = json.load(f)

        if not search_term or search_term.lower() == "all":
            return illustrations

        # Handle common singular/plural conversions
        search_terms = [search_term]
        if search_term.endswith("s"):
            # Add singular form (remove trailing 's')
            search_terms.append(search_term[:-1])
        else:
            # Add plural form (add 's')
            search_terms.append(search_term + "s")

        # Create a dictionary where keys are image files and values are searchable strings
        choices = {img["file"]: f"{img['title']} {' '.join(img['tags'])}" for img in illustrations}

        all_matches = []
        for term in search_terms:
            # Use thefuzz to find matches
            found_matches = process.extract(term, choices, limit=10)
            # Lower the threshold to 55 to be more lenient
            matches = [{"file": key} for match, score, key in found_matches if score >= 55]
            all_matches.extend(matches)

        # Remove duplicates
        unique_matches = []
        seen_files = set()
        for match in all_matches:
            if match["file"] not in seen_files:
                unique_matches.append(match)
                seen_files.add(match["file"])

        # Convert file names back to full illustration objects
        results = []
        for match in unique_matches:
            for img in illustrations:
                if img["file"] == match["file"]:
                    results.append(img)
                    break

        return results
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return []


@pytest.mark.integration
def test_search_illustrations():
    # Test searching for "snakes" (plural)
    results = search_illustrations("snakes")

    # Print the results
    print(f"Found {len(results)} results for 'snakes':")
    for img in results:
        print(f"- {img['file']}: {img['title']} (tags: {', '.join(img['tags'])})")

    # Check if any results contain "snake" in tags
    snake_images = [img for img in results if "snake" in img["tags"]]
    print(f"\nFound {len(snake_images)} images with 'snake' tag:")
    for img in snake_images:
        print(f"- {img['file']}: {img['title']} (tags: {', '.join(img['tags'])})")

    # Test searching for "snake" (singular)
    results_singular = search_illustrations("snake")
    print(f"\nFound {len(results_singular)} results for 'snake':")
    for img in results_singular:
        print(f"- {img['file']}: {img['title']} (tags: {', '.join(img['tags'])})")


if __name__ == "__main__":
    test_search_illustrations()
