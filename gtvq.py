from typing import List
from enum import Enum
import sys


command_lookup_table = {}  # COMMAND -> function call

# Things used by commands
functions = {}
variables = [{}]  # List of scopes
callstack_depth = 0


class Line:
    """Represents a tokenized line.
    """
    def __init__(self):
        self.__command = ""
        self.__parameters: List[str] = []

    def get_command(self):
        return self.__command

    def add_parameter(self, parameter):
        if self.__command == "":
            self.__command = parameter.upper()
        else:
            self.__parameters.append(parameter)

    def get_parameters(self):
        return self.__parameters

    def __str__(self):
        return "LINE<" + self.__command + ":" + "|".join(self.__parameters) + ">"


def register_command(command: str, function_pointer: callable):
    command = command.upper().strip()
    command_lookup_table[command] = function_pointer


def try_call_command(command: str, parameters: List[str]) -> str:
    """Tries to call a function registered to a command and returns its return value.
    """
    command = command.upper().strip()
    if command not in command_lookup_table:
        error(f"Command {command} not registered as a valid command.")
    return command_lookup_table[command](parameters)


def error(message: str):
    print(f"Error: {message}")
    sys.exit(1)


def tokenize_source(file_contents: str) -> List[Line]:
    """Takes the contents of a source file and tokenizes each line.
    """
    file_contents += ";"
    lines = []
    current_line = Line()
    next_char_is_escaped: bool = False
    current_token: str = ""
    current_string: str = ""
    parsing_string: bool = False
    current_square_block_level: int = 0
    current_par_block_level: int = 0
    in_comment: bool = False
    for char in file_contents:
        if parsing_string:
            # String Parsing
            if not next_char_is_escaped:
                if char == '"':
                    # Exit string
                    current_token += char
                    if current_square_block_level == 0 and current_par_block_level == 0:
                        current_line.add_parameter(current_token)
                        current_token = ""
                    parsing_string = False
                    continue
                elif char == "\\":
                    # Next character will be escaped
                    next_char_is_escaped = True
            else:
                # Replace escaped characters that can be added to a string
                # Otherwise the character after \ is left as-is
                if char == "n":
                    char = "\n"
                elif char == "t":
                    char = "\t"
                next_char_is_escaped = False
            current_token = current_token + char
        elif in_comment:
            if char == "!":
                in_comment = False
        elif char == "!" and not in_comment and (current_square_block_level == 0 and current_par_block_level == 0):
            in_comment = True
        elif char in " \r\t\n\"()}{;":
            # Closure characters
            if char == "}":
                current_square_block_level -= 1
                current_token += char
            elif char == ")":
                current_par_block_level -= 1
                current_token += char
            # Command pushing
            if current_square_block_level == 0 and current_par_block_level == 0:
                # Whitespace characters
                if len(current_token) > 0:
                    current_line.add_parameter(current_token)
                    current_token = ""
                # Check individual special chars
                if char in "\n;":
                    if current_line.get_command():
                        lines.append(current_line)
                        current_line = Line()
            if current_square_block_level > 0 or current_par_block_level > 0:
                if char in "\n; ":
                    current_token += char
            # Opening characters
            if char == "\"":
                parsing_string = True
                current_token += char
            elif char == "{":
                current_square_block_level += 1
                current_token += char
            elif char == "(":
                current_par_block_level += 1
                current_token += char
        else:
            current_token += char

    # Check for errors
    if current_par_block_level > 0:
        error("Missing ) - open (...)")
    if current_square_block_level > 0:
        error("Missing } - open {...}")
    if parsing_string:
        error("Missing \" - open \"...\"")
    if in_comment:
        error("Missing ! - open comment.")
        
    return lines


def execute_line(line: Line) -> str:
    """Executes a tokenized line and returns its return value
    """
    command = line.get_command()
    parameters = line.get_parameters()
    # First, execute all executable arguments (...)
    for i in range(0, len(parameters)):
        if parameters[i][0] == "(":
            new_code = parameters[i][1:-1]
            return_value: str = execute_code(new_code)
            parameters[i] = return_value
    # Next execute the line
    return try_call_command(command, parameters)


def execute_code(code: str) -> str:
    """Executes code written in this language.
    """
    code = code.strip()
    lines = tokenize_source(code)
    last_return_value = ""
    for line in lines:
        last_return_value = execute_line(line)
    return last_return_value


if __name__ == "__main__":

    def display_command(parameters: List[str]):
        for parameter in parameters:
            parameter = str(parameter)
            if parameter[0] == '"' and parameter[-1] == '"':
                print(parameter[1:-1], end="")
            else:
                print(parameter, end="")
        print("")
        return ""

    def set_command(parameters: List[str]):
        global variables
        variables[-1][parameters[0]] = parameters[1]
        return ""

    def get_command(parameters: List[str]):
        global variables
        for scope in variables[::-1]:
            if parameters[0] in scope:
                return scope[parameters[0]]
        error(f"Variable {parameters[0]} not set.")

    def gset_command(parameters: List[str]):
        global variables
        variables[0][parameters[0]] = parameters[1]
        return ""

    def gget_command(parameters: List[str]):
        global variables
        if parameters[0] in variables[0]:
            return variables[0][parameters[0]]
        error(f"Global variable {parameters[0]} not set.")

    def exec_command(parameters: List[str]):
        return execute_code(parameters[0][1:-1])

    def def_command(parameters: List[str]):
        global functions
        if parameters[1] != ":":
            error(f"Please use : for declaring a function ({parameters[0]})")
        functions[parameters[0]] = (parameters[2:-1], parameters[-1])
        return parameters[0]

    def call_command(parameters: List[str]):
        global functions
        variables.append({})
        function_name = parameters[0]
        if function_name not in functions:
            error(f"Unknown function {function_name}.")
        else:
            function_object = functions[function_name]
            function_arguments = function_object[0]
            function_code = function_object[1][1:-1]
            for i in range(0, len(function_arguments)):
                if i > len(parameters) - 1:
                    error(f"No value provided for parameter {function_arguments[i]} of function {function_name}.")
                else:
                    #function_code = function_code.replace(function_arguments[i], parameters[i+1])
                    execute_code(f"set {function_arguments[i]} {parameters[i+1]}")
            return_value = execute_code(function_code)
        variables.pop()
        return return_value

    def accept_command(parameters: List[str]):
        if parameters[0][0] == '"' and parameters[0][-1] == '"':
            return input(parameters[0][1:-1])
        else:
            return input(parameters[0])

    def for_command(parameters: List[str]):
        iteration_variable = parameters[0]
        min_value = int(parameters[2])
        max_value = int(parameters[4])
        function_code = parameters[5][1:-1]
        if max_value >= min_value:
            for i in range(min_value, max_value):
                execute_code(f"set {iteration_variable} {i}")
                execute_code(function_code)
        else:
            for i in range(min_value, max_value, -1):
                execute_code(f"set {iteration_variable} {i}")
                execute_code(function_code)


    def return_command(parameters: List[str]):
        return parameters[0]

    def if_command(parameters: List[str]):
        condition_code = parameters[0][1:-1]
        true_branch = parameters[1][1:-1]
        result = int(execute_code(condition_code)) == 1
        if result:
            return execute_code(true_branch)
        if len(parameters) == 4:
            if not result:
                return execute_code(parameters[3][1:-1]) # else branch
        return '""'
        # elif case, ir checkeando dos a dos

    def mod_command(parameters: List[str]):
        return int(parameters[0]) % int(parameters[1])
        # elif case, ir checkeando dos a dos

    def eq_command(parameters: List[str]):
        if int(parameters[0]) == int(parameters[1]):
            return 1
        else:
            return 0

    def neq_command(parameters: List[str]):
        if int(parameters[0]) != int(parameters[1]):
            return 1
        else:
            return 0

    def plus_command(parameters: List[str]):
        return int(parameters[0]) + int(parameters[1])

    def sub_command(parameters: List[str]):
        return int(parameters[0]) - int(parameters[1])

    def lt_command(parameters: List[str]):
        if int(parameters[0]) < int(parameters[1]):
            return 1
        else:
            return 0

    def gt_command(parameters: List[str]):
        if int(parameters[0]) > int(parameters[1]):
            return 1
        else:
            return 0

    def join_command(parameters: List[str]):
        return str(parameters[0]) + str(parameters[1])

    def varex_command(parameters: List[str]):
        global variables
        for scope in variables[::-1]:
            if parameters[0] in scope:
                return 1
        return 0

    def and_command(parameters: List[str]):
        if int(parameters[0]) == 1 and int(parameters[1]) == 1:
            return 1
        else:
            return 0

    register_command("display", display_command)
    register_command("set", set_command)
    register_command("get", get_command)
    register_command("gset", gset_command)
    register_command("gget", gget_command)
    register_command("exec", exec_command)
    register_command("def", def_command)
    register_command("call", call_command)
    register_command("accept", accept_command)
    register_command("for", for_command)
    register_command("return", return_command)
    register_command("if", if_command)
    register_command("mod", mod_command)
    register_command("%", mod_command)
    register_command("==", eq_command)
    register_command("<>", neq_command)
    register_command("+", plus_command)
    register_command("-", sub_command)
    register_command("<", lt_command)
    register_command(">", gt_command)
    register_command("join", join_command)
    register_command("varex", varex_command)
    register_command("and", and_command)

    file_contents = ""
    with open(sys.argv[1], "r") as file:
    #with open("code.lang", "r") as file:
        file_contents = file.read()
    execute_code(file_contents)