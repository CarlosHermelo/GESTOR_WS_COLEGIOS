import sys
import os
from datetime import datetime
import argparse

# Base path for memory files
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")

def add_entry(category, text, tags=None):
    filename = f"{category}.md"
    filepath = os.path.join(MEMORY_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"Error: Category {category} not found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags_str = f" [Tags: {tags}]" if tags else ""
    
    entry = f"\n### [{timestamp}]{tags_str}\n{text}\n---\n"
    
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)
    
    print(f"Entry added to {filename}.")

def search_memory(query):
    results = []
    for filename in os.listdir(MEMORY_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(MEMORY_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                if query.lower() in content.lower():
                    results.append(filename)
    
    if not results:
        print(f"No matches found for '{query}'.")
    else:
        print(f"Found matches in: {', '.join(results)}")
        # For a real implementation, we might want to return snippets, 
        # but for now, listing files is a good start.

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Triple Memory for Project Maestro")
    subparsers = parser.add_subparsers(dest="command")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new memory entry")
    add_parser.add_argument("category", choices=["reminders", "knowledge_base", "technical_norms"])
    add_parser.add_argument("text", help="The memory content")
    add_parser.add_argument("--tags", help="Comma-separated tags")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search in memory")
    search_parser.add_argument("query", help="Text to search for")

    args = parser.parse_args()

    if args.command == "add":
        add_entry(args.category, args.text, args.tags)
    elif args.command == "search":
        search_memory(args.query)
    else:
        parser.print_help()
