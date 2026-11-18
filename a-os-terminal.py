import ast
import datetime
import getpass
import operator
import os
import shlex
import shutil
import subprocess
import sys


da = "Successfully ended system"
versi = "A-OS V3.1"
PARTITION_ROOT = os.path.abspath(os.getcwd())
ACTIVE_PARTITION = "main"


def path(value):
    return os.path.expanduser(value)


def show_tree(root=".", prefix="", depth=0, max_depth=4):
    if depth >= max_depth:
        return
    try:
        entries = sorted(os.listdir(root))
    except OSError as error:
        print("{}: {}".format(root, error))
        return
    entries = [name for name in entries if not name.startswith(".")]
    for index, name in enumerate(entries):
        last = index == len(entries) - 1
        print("{}{}{}".format(prefix, "└── " if last else "├── ", name))
        full_path = os.path.join(root, name)
        if os.path.isdir(full_path) and not os.path.islink(full_path):
            show_tree(full_path, prefix + ("    " if last else "│   "), depth + 1, max_depth)


def calculate(expression):
    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Num):
            return node.n
        if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("only numbers are allowed")
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.operand))
        raise ValueError("use numbers and +, -, *, /, //, %, or **")

    return evaluate(ast.parse(expression, mode="eval"))


def edit_python(filename=None):
    code_lines = []
    if filename:
        filename = path(filename)
        if os.path.isfile(filename):
            with open(filename, "r") as file:
                code_lines = file.read().splitlines()
            print("Opened {}".format(filename))
        else:
            print("New Python file: {}".format(filename))

    print("Python editor.")
    print("Commands: :run, :save [file.py], :clear, :quit, :help")
    if code_lines:
        print("--- current code ---")
        for number, code_line in enumerate(code_lines, 1):
            print("{:>3} | {}".format(number, code_line))
        print("--- add or edit lines below; use :clear to start over ---")

    while True:
        try:
            if sys.stdin.isatty():
                line = input("... ")
            else:
                line = sys.stdin.readline()
                if not line:
                    return True
                line = line.rstrip("\r\n")
        except EOFError:
            return True

        if line == ":run":
            source = "\n".join(code_lines)
            try:
                namespace = {"__name__": "__main__", "__file__": filename or "<pyrun>"}
                exec(compile(source, filename or "<pyrun>", "exec"), namespace)
            except Exception as error:
                print("Python error: {}".format(error))
            print("--- editor ready ---")
        elif line.startswith(":save"):
            try:
                parts = shlex.split(line[1:])
                save_as = parts[1] if len(parts) > 1 else filename
                if not save_as:
                    print("Choose a filename: :save my_program.py")
                    continue
                filename = path(save_as)
                parent = os.path.dirname(filename)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                with open(filename, "w") as file:
                    file.write("\n".join(code_lines))
                    if code_lines:
                        file.write("\n")
                print("Saved {}".format(filename))
            except (OSError, ValueError) as error:
                print("Save error: {}".format(error))
        elif line == ":clear":
            code_lines = []
            print("Code cleared.")
        elif line == ":help":
            print("Type Python code, then :run. Use :save [file.py] to save,")
            print(":clear to erase the editor, or :quit to leave.")
        elif line == ":quit":
            print(da)
            return True
        else:
            code_lines.append(line)


def open_layout():
    import tkinter as tk
    from tkinter import ttk

    try:
        window = tk.Tk()
    except tk.TclError as error:
        print("Layout window unavailable: {}".format(error))
        return

    window.title("A-OS Layout")
    window.geometry("720x460")
    base_path = os.path.abspath(os.getcwd())
    state = {"section": None, "folder": base_path}

    top = ttk.Frame(window, padding=(10, 8))
    top.pack(fill="x")
    breadcrumb = ttk.Frame(top)
    breadcrumb.pack(side="left", fill="x", expand=True)
    ttk.Button(top, text="Home", command=lambda: show_home()).pack(side="right")

    body = ttk.Frame(window, padding=(10, 0, 10, 8))
    body.pack(fill="both", expand=True)
    listing = ttk.Treeview(body, columns=("kind", "location"), show="headings")
    listing.heading("kind", text="Type")
    listing.heading("location", text="Location")
    listing.column("kind", width=100, stretch=False)
    listing.column("location", width=440)
    listing.pack(fill="both", expand=True)
    details = ttk.Label(window, text="Hover over an item to see details.", anchor="w", padding=8)
    details.pack(fill="x")

    programs = [
        ("calc", "Calculate a math expression"),
        ("tree", "Explore folders in the terminal"),
        ("date", "Show the computer's clock"),
        ("pyrun / edit", "Write and run Python programs"),
        ("computer", "Show computer information"),
    ]

    def set_breadcrumbs():
        for child in breadcrumb.winfo_children():
            child.destroy()
        ttk.Button(breadcrumb, text="PC", command=show_home).pack(side="left")
        section = state["section"]
        if section:
            ttk.Label(breadcrumb, text=" > ").pack(side="left")
            ttk.Button(breadcrumb, text=section, command=lambda: show_section(section)).pack(side="left")
        if section == "Files":
            relative = os.path.relpath(state["folder"], base_path)
            if relative != ".":
                current = base_path
                for part in relative.split(os.sep):
                    current = os.path.join(current, part)
                    target = current
                    ttk.Label(breadcrumb, text=" > ").pack(side="left")
                    ttk.Button(
                        breadcrumb,
                        text=part,
                        command=lambda folder=target: show_folder(folder),
                    ).pack(side="left")

    def clear_listing():
        for item in listing.get_children():
            listing.delete(item)

    def show_home():
        state["section"] = None
        state["folder"] = base_path
        clear_listing()
        set_breadcrumbs()
        for name, description in (("Programs", "Browse built-in programs"), ("Files", "Browse files from {}".format(base_path))):
            listing.insert("", "end", values=("Section", description), text=name, iid=name)
        listing.bind("<Double-1>", open_home_item)
        details.config(text="PC — choose Programs or Files. Double-click an item to open it.")

    def open_home_item(event):
        item = listing.identify_row(event.y)
        if item in ("Programs", "Files"):
            show_section(item)

    def show_section(section):
        state["section"] = section
        clear_listing()
        set_breadcrumbs()
        if section == "Programs":
            for name, description in programs:
                listing.insert("", "end", iid="program:" + name, values=("Program", description))
            listing.bind("<Double-1>", lambda event: None)
            details.config(text="Programs — hover over an item to see what it does.")
        else:
            show_folder(base_path)

    def show_folder(folder):
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return
        state["section"] = "Files"
        state["folder"] = folder
        clear_listing()
        set_breadcrumbs()
        try:
            entries = sorted(os.scandir(folder), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                kind = "Folder" if entry.is_dir() else "File"
                listing.insert("", "end", iid=entry.path, values=(kind, entry.path))
        except OSError as error:
            details.config(text="Could not list folder: {}".format(error))
        listing.bind("<Double-1>", open_file_item)
        details.config(text="{} — hover over an item for its location and details.".format(folder))

    def item_details(item):
        if not item:
            return
        values = listing.item(item, "values")
        if not values:
            return
        kind, location = values
        if kind == "Program":
            description = next((text for name, text in programs if name == item[len("program:"):]), "Built-in program")
            details.config(text="{} — {}".format(item[len("program:"):], description))
        elif kind == "Section":
            details.config(text="{} — {}".format(item, location))
        else:
            try:
                if kind == "Folder":
                    details.config(text="Folder: {}".format(location))
                else:
                    size = os.path.getsize(location)
                    details.config(text="File: {}  |  {} bytes".format(location, size))
            except OSError as error:
                details.config(text="{} — {}".format(location, error))

    def hover_item(event):
        item = listing.identify_row(event.y)
        item_details(item)

    def select_item(event):
        item_details(listing.identify_row(event.y))

    def open_file_item(event):
        item = listing.identify_row(event.y)
        if not item:
            return
        kind, location = listing.item(item, "values")
        if kind == "Folder":
            show_folder(location)
        else:
            item_details(item)

    listing.bind("<Motion>", hover_item)
    listing.bind("<ButtonRelease-1>", select_item)
    show_home()
    window.mainloop()


def browse_branch():
    """Browse files under the current folder and choose an action for a file."""
    while True:
        files = []
        for folder, directories, filenames in os.walk(os.getcwd()):
            directories[:] = sorted(
                name for name in directories
                if not name.startswith(".")
            )
            for filename in sorted(filenames):
                if filename.startswith("."):
                    continue
                full_path = os.path.join(folder, filename)
                files.append(os.path.relpath(full_path, os.getcwd()))

        print("Files in {}:".format(os.getcwd()))
        if files:
            for filename in files:
                print("  {}".format(filename))
        else:
            print("  (no files found)")

        try:
            selection = input("{} [branch] filename or back: ".format(os.getcwd())).strip()
        except EOFError:
            return
        if selection.lower() == "back":
            return
        target = os.path.abspath(os.path.join(os.getcwd(), selection))
        if not os.path.isfile(target):
            print("File not found: {}".format(selection))
            continue

        while True:
            try:
                action = input("{} [edit/delete/back]: ".format(target)).strip().lower()
            except EOFError:
                return
            if action == "back":
                break
            if action == "edit":
                edit_python(target)
                break
            if action == "delete":
                try:
                    os.remove(target)
                    print("Deleted {}".format(target))
                except OSError as error:
                    print("Delete error: {}".format(error))
                break
            print("Choose edit, delete, or back.")


def run_builtin(command, args):
    if command == "pwd":
        print(os.getcwd())
    elif command == "cd":
        os.chdir(path(args[0]) if args else os.path.expanduser("~"))
    elif command == "ls":
        show_all = "-a" in args or "-la" in args or "-al" in args
        targets = [item for item in args if not item.startswith("-")] or ["."]
        for target in targets:
            entries = os.listdir(path(target))
            if not show_all:
                entries = [name for name in entries if not name.startswith(".")]
            if len(targets) > 1:
                print("{}:".format(target))
            print("  ".join(sorted(entries)))
    elif command == "mkdir":
        parents = "-p" in args
        for item in args:
            if not item.startswith("-"):
                os.makedirs(path(item), exist_ok=parents)
    elif command == "touch":
        for item in args:
            with open(path(item), "a"):
                os.utime(path(item), None)
    elif command == "new":
        if not args:
            raise ValueError("usage: new FILE.py")
        filename = path(args[0])
        with open(filename, "a"):
            pass
        edit_python(filename)
    elif command in ("pyrun", "edit"):
        edit_python(args[0] if args else None)
    elif command == "rm":
        recursive = "-r" in args or "-R" in args or "-rf" in args or "-fr" in args
        force = "-f" in args or "-rf" in args or "-fr" in args
        for item in args:
            if item.startswith("-"):
                continue
            target = path(item)
            if os.path.isdir(target) and not os.path.islink(target):
                if recursive:
                    shutil.rmtree(target)
                else:
                    os.rmdir(target)
            elif os.path.exists(target) or os.path.islink(target):
                os.remove(target)
            elif not force:
                raise FileNotFoundError(item)
    elif command == "cp":
        recursive = "-r" in args or "-R" in args
        items = [path(item) for item in args if not item.startswith("-")]
        if len(items) != 2:
            raise ValueError("usage: cp [-r] SOURCE DEST")
        source, destination = items
        if os.path.isdir(source):
            if not recursive:
                raise ValueError("cp: omitting directory '{}' (use -r)".format(source))
            if sys.version_info >= (3, 8):
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                if os.path.exists(destination):
                    raise ValueError("destination already exists")
                shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    elif command == "mv":
        items = [path(item) for item in args if not item.startswith("-")]
        if len(items) != 2:
            raise ValueError("usage: mv SOURCE DEST")
        shutil.move(items[0], items[1])
    elif command == "cat":
        for item in args:
            with open(path(item), "r") as file:
                sys.stdout.write(file.read())
    elif command == "echo":
        print(" ".join(args))
    elif command == "whoami":
        try:
            print(getpass.getuser())
        except (KeyError, OSError):
            print(os.environ.get("USER") or os.environ.get("USERNAME") or "unknown")
    elif command == "branch":
        browse_branch()
    elif command == "partition":
        if len(args) == 2 and args[0] == "add":
            name = args[1]
            if name == "main" or name in (".", "..") or os.path.basename(name) != name:
                raise ValueError("choose a simple partition name other than 'main'")
            partition_path = os.path.join(PARTITION_ROOT, ".aos_partitions", name)
            os.makedirs(partition_path, exist_ok=True)
            print("Partition '{}' is ready.".format(name))
        elif len(args) == 2 and args[0] == "switch":
            name = args[1]
            if name == "main":
                partition_path = PARTITION_ROOT
            else:
                partition_path = os.path.join(PARTITION_ROOT, ".aos_partitions", name)
            if not os.path.isdir(partition_path):
                raise ValueError("partition '{}' does not exist; use partition add {}".format(name, name))
            os.chdir(partition_path)
            global ACTIVE_PARTITION
            ACTIVE_PARTITION = name
            print("Switched to partition '{}' ({})".format(name, os.getcwd()))
        else:
            raise ValueError("usage: partition add NAME | partition switch NAME")
    elif command == "why":
        print("A-OS is a simple layout on top of this terminal. This is not a linux terminal; it is a basic light-weitght a-os.")
    elif command == "help":
        print("A-OS computer commands:")
        print("  ls, cd, pwd, mkdir, new, touch, cat, cp, mv, rm, tree, branch")
        print("  pyrun [file.py], edit [file.py], programs, computer, calc, date")
        print("  partition add NAME, partition switch NAME")
        print("  echo, clear, help, exit")
        print("Use quotes around file names or text that contains spaces.")
    elif command == "programs":
        print("Installed programs:")
        print("  pyrun / edit  - write and run Python programs")
        print("  calc          - calculate a math expression")
        print("  tree          - explore folders")
        print("  date          - show the computer's clock")
        print("  computer      - show computer information")
    elif command == "computer":
        print("A-OS Computer")
        print("OS: {}".format(versi))
        print("Python: {}.{}.{}".format(*sys.version_info[:3]))
        print("Folder: {}".format(os.getcwd()))
        print("Partition: {}".format(ACTIVE_PARTITION))
        print("Programs: pyrun, calc, tree, date, branch")
    elif command == "tree":
        root = path(args[0]) if args else "."
        print(root)
        show_tree(root)
    elif command == "calc":
        if not args:
            raise ValueError("usage: calc EXPRESSION (example: calc 12 * 8)")
        print(calculate(" ".join(args)))
    elif command == "date":
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    elif command == "clear":
        print("\n" * 40)
    elif command == "exit":
        print(da)
        return False
    else:
        return None
    return True


def main():
    interactive = sys.stdin.isatty()
    print("Welcome to A-OS!")
    print(versi)
    print("TERMINAL ==================")
    print("Say 'help' for help or 'programs' to see the programs.")

    while True:
        try:
            prompt_name = "a-os" if ACTIVE_PARTITION == "main" else ACTIVE_PARTITION
            line = input("root@{}: $ ".format(prompt_name))
        except EOFError:
            break
        if not line:
            break
        args = []
        try:
            args = shlex.split(line)
            if not args:
                continue
            if args[0] == "partiton":
                args[0] = "partition"
            shell_syntax = any(symbol in line for symbol in ("|", ">", "<", ";", "&", "$", "`"))
            if shell_syntax:
                subprocess.call(line, shell=True)
                continue
            result = run_builtin(args[0], args[1:])
            if result is False:
                break
            if result is None:
                subprocess.call(line, shell=True)
        except (OSError, ValueError, SyntaxError) as error:
            print("{}: {}".format(args[0] if args else "error", error))


if __name__ == "__main__":
    main()
