import os
import re
import argparse

from graphviz import Digraph
from emacs_builtin_packages import EMACS_BUILTIN_PACKAGES
from emacs_package_metadata import PACKAGE_DESCRIPTIONS, CATEGORY_HIERARCHY, GRAPH_TITLE_FORMAT


def find_emacs_package_dependencies(repo_path: str, only_main_file: bool = False) -> dict[str, set[str]]:
    """
    Reads an Emacs package repository path, iterates through each package's .el files,
    finds "Package-Requires:" lines, and returns a dictionary of package dependencies.

    Args:
        repo_path: The file system path to the Emacs package repository.
                   This directory should contain subdirectories for each package.
        only_main_file: If True, only search for dependencies in the main .el file.
                       The main file is either:
                       1. The .el file that matches the package directory name, or
                       2. The only .el file in the directory if there's just one.
                       If False, search in all .el files in the package directory.

    Returns:
        A dictionary where keys are package names (string) and values are sets
        of dependency package names (strings). Version numbers are ignored.
        Example: {'citar': {'emacs', 'parsebib', 'org', 'citeproc'}}
    """
    all_dependencies: dict[str, set[str]] = {}

    # Regex to find the Package-Requires line and capture the list of dependencies.
    package_requires_regex = re.compile(
        r"^\s*;;;?\s*Package-Requires:\s*\((.*)\)\s*$", re.IGNORECASE
    )

    # Regex to extract individual package names from the captured dependency list string.
    # A dependency in the list can be of the form (package-name "version") or package-name (a symbol).
    dependency_item_regex = re.compile(r"\(([\w-]+)[^)]*\)|([\w-]+)")

    if not os.path.isdir(repo_path):
        print(f"Error: Path '{repo_path}' is not a valid directory.")
        return all_dependencies

    for entry_name in os.listdir(repo_path):
        package_dir_path = os.path.join(repo_path, entry_name)
        if os.path.isdir(package_dir_path):
            # Determine the package name (key for the dictionary).
            # If a directory name is "foo.el", the package name is "foo".
            # Otherwise, the directory name is used as the package name.
            package_name_key = entry_name
            if entry_name.endswith(".el") and not entry_name.startswith("."):
                package_name_key = entry_name[:-3]

            # Use .get to ensure that if multiple directory names map to the same
            # package_name_key (e.g., 'foo' and 'foo.el' directories),
            # their dependencies are merged.
            current_package_deps: set[str] = all_dependencies.get(package_name_key, set())

            el_files = [f for f in os.listdir(package_dir_path) if f.endswith('.el')]

            # If only searching main file, determine which file is the main file
            main_file = None
            if only_main_file:
                # If there's only one .el file, it's the main file
                if len(el_files) == 1:
                    main_file = el_files[0]
                # Otherwise try to find the .el file matching the directory name
                else:
                    main_file = f"{package_name_key}.el"
                    if main_file not in el_files:
                        main_file = None

            for item_in_package_dir in el_files:
                # Skip non-main files if only searching main file
                if only_main_file and item_in_package_dir != main_file:
                    continue

                el_file_path = os.path.join(package_dir_path, item_in_package_dir)
                try:
                    with open(el_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            match = package_requires_regex.search(line)
                            if match:
                                # dependencies_str is the content within the outer parens
                                # e.g., "(emacs "27.1") (parsebib "4.2")" or "pkg-a (pkg-b "1.0")"
                                dependencies_str = match.group(1).strip()

                                if not dependencies_str:
                                    continue

                                found_deps_on_line = dependency_item_regex.findall(dependencies_str)
                                for group1, group2 in found_deps_on_line:
                                    dep_name = group1 if group1 else group2
                                    if dep_name:
                                        current_package_deps.add(dep_name)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"Warning: Error reading or processing file '{el_file_path}': {e}")

            all_dependencies[package_name_key] = current_package_deps
            if not current_package_deps and package_name_key not in all_dependencies:  # Ensure packages with no deps are also listed
                all_dependencies[package_name_key] = set()

    return all_dependencies

def generate_dependency_graph(dependencies: dict[str, set[str]], output_file: str = "emacs_dependencies", emacs_version: str = "30", show_descriptions: bool = False, repo_path: str = None) -> None:
    """
    Generate a dependency graph for Emacs packages.

    Args:
        dependencies: Dictionary of package dependencies
        output_file: Output filename (without extension)
        emacs_version: Emacs version to determine built-in packages
        show_descriptions: Whether to show package descriptions in the graph
        repo_path: Path to the repository, used in the graph title
    """
    dot = Digraph(comment='Emacs Package Dependencies')
    dot.attr(rankdir='LR')  # Left to right layout
    
    title = GRAPH_TITLE_FORMAT.format(repo=repo_path)
    dot.attr(label=title, fontsize='20', fontname='Arial')

    # Set default node attributes
    dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')

    # Get built-in packages for the specified version
    builtin_packages = EMACS_BUILTIN_PACKAGES.get(emacs_version, set())

    def create_node(package, parent_graph, label=None):
        """Helper function to create a node"""
        if label is None:
            label = package
        if show_descriptions and package in PACKAGE_DESCRIPTIONS:
            label = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2">
                <TR><TD ALIGN="left">{package}</TD></TR>
                <TR><TD ALIGN="left"><FONT POINT-SIZE="9">{PACKAGE_DESCRIPTIONS[package]}</FONT></TD></TR>
            </TABLE>>'''
        
        if package in builtin_packages:
            parent_graph.node(package, label, fillcolor='lightblue')
        else:
            parent_graph.node(package, label, fillcolor='lightgrey')

    def create_category_subgraph(parent_graph, category_name, content):
        """Helper function to create category subgraph, supporting arbitrary depth
        
        Args:
            parent_graph: Parent graph object
            category_name: Category name
            content: Category content, can be a package list or subcategory dictionary
        """
        with parent_graph.subgraph(name=f'cluster_{category_name}') as s:
            s.attr(label=category_name)
            s.attr(style='rounded')

            if isinstance(content, list):
                # If it's a package list, create nodes directly
                for package in content:
                    if package in dependencies:
                        create_node(package, s)
            else:
                # If it's a dictionary, process subcategories first
                for subcategory, subcontent in content.items():
                    if subcategory != 'packages':  # Skip special 'packages' key
                        create_category_subgraph(s, subcategory, subcontent)
                
                # Then process packages directly belonging to this category
                if 'packages' in content:
                    for package in content['packages']:
                        if package in dependencies:
                            create_node(package, s)
            return s

    # Create nested category structure
    for category_name, content in CATEGORY_HIERARCHY.items():
        create_category_subgraph(dot, category_name, content)

    # Create nodes for packages not in any category
    def get_all_packages(category_dict):
        """Recursively get all packages"""
        packages = set()
        for content in category_dict.values():
            if isinstance(content, list):
                packages.update(content)
            else:
                packages.update(get_all_packages(content))
        return packages

    all_categorized_packages = get_all_packages(CATEGORY_HIERARCHY)
    for package in dependencies.keys():
        if package not in all_categorized_packages:
            create_node(package, dot)

    # Add all edges (dependencies)
    for package, deps in dependencies.items():
        for dep in deps:
            if dep in dependencies:  # Only add packages that exist in the dependency dict
                dot.edge(package, dep)

    # Save the image
    dot.render(output_file, format='png', cleanup=True)
    print(f"\n📊 Dependency graph saved as: {output_file}.png")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Emacs package dependencies from a repository directory.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Common arguments for all subcommands
    parser.add_argument(
        '--only-main-file',
        action='store_true',
        default=True,
        help='Only search for dependencies in the main .el file of each package'
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Text output command
    text_parser = subparsers.add_parser('text', help='Output dependencies in text format')
    text_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to the Emacs package repository directory'
    )
    text_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format for the dependencies'
    )
    
    # Graph output command
    graph_parser = subparsers.add_parser('graph', help='Generate dependency graph')
    graph_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to the Emacs package repository directory'
    )
    graph_parser.add_argument(
        '--output-file',
        type=str,
        default='emacs_dependencies',
        help='Output filename for the graph (without extension)'
    )
    graph_parser.add_argument(
        '--emacs-version',
        type=str,
        default='30',
        choices=list(EMACS_BUILTIN_PACKAGES.keys()),
        help='Emacs version to determine built-in packages'
    )
    graph_parser.add_argument(
        '--show-descriptions',
        action='store_true',
        help='Show package descriptions in the graph'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    dependencies = find_emacs_package_dependencies(args.repo_path, args.only_main_file)
    
    if args.command == 'text':
        if args.format == 'json':
            import json
            print(json.dumps({k: list(v) for k, v in dependencies.items()}, indent=2))
        else:
            print("\n📊 Detected Package Dependencies:")
            if dependencies:
                for pkg, deps in dependencies.items():
                    print(f"  - {pkg}: {deps if deps else '{}'}")
            else:
                print("  No dependencies found or error in processing.")
    elif args.command == 'graph':
        generate_dependency_graph(dependencies, args.output_file, args.emacs_version, args.show_descriptions, args.repo_path)


if __name__ == '__main__':
    main()
