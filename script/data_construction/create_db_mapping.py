#!/usr/bin/env python3
"""
Script to generate a mapping from function name to database.
Reads tools.json for the list of tools and user_queries.json for the database association.
"""

import json
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(script_dir))
    tools_file = os.path.join(base_dir, "data", "tools.json")
    queries_file = os.path.join(base_dir, "user_queries.json")
    output_file = os.path.join(base_dir, "data", "function_mapping.json")

    print(f"Loading tools from {tools_file}...")
    try:
        with open(tools_file, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
    except Exception as e:
        print(f"Error loading tools file: {e}")
        sys.exit(1)

    print(f"Loading queries from {queries_file}...")
    try:
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries_data = json.load(f)
    except Exception as e:
        print(f"Error loading queries file: {e}")
        sys.exit(1)

    # Extract mapping from queries
    # user_queries.json seems to be a list of objects with "function" and "database" keys
    
    func_to_db = {}
    
    print("Building mapping from user queries...")
    for entry in queries_data:
        func_name = entry.get('function')
        db_name = entry.get('database')
        
        if func_name and db_name:
            if func_name in func_to_db and func_to_db[func_name] != db_name:
                print(f"Warning: Function '{func_name}' associated with multiple databases: {func_to_db[func_name]} and {db_name}")
            func_to_db[func_name] = db_name

    # Verify against tools.json
    print("Verifying against available tools...")
    tool_names = set()
    for tool in tools_data:
        # tools.json is a list of objects like {"type": "function", "function": {"name": ...}}
        if isinstance(tool, dict) and 'function' in tool:
            t_name = tool['function'].get('name')
            if t_name:
                tool_names.add(t_name)
    
    missing = []
    for name in tool_names:
        if name not in func_to_db:
            missing.append(name)
    
    if missing:
        print(f"Warning: {len(missing)} tools defined in tools.json but not found in user_queries.json:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("All tools in tools.json have a database mapping.")

    print(f"Mapped {len(func_to_db)} functions to databases.")

    # Write output
    print(f"Writing mapping to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(func_to_db, f, indent=2)
    
    print("Done.")

if __name__ == "__main__":
    main()



