#!/usr/bin/env python3

import re
import argparse
import os


class parseline(object):
    """ Parses line to A- or C-type instruction.

    Attributes:
        line (str): line from asm, usually sanitized.
        line_loc (int): optional line number specification.
        symbolics (symboltable): optional reference to symbolic table
            instance.
        type (str): a_type or c_type instruction
        binary (str(016b)): binary string of parsed instruction.

    Todo:

    """

    def __init__(self, line, line_loc=None, symbolics=None):
        self.line = _sanitizeline(line)
        self.line_loc = line_loc
        self.type, self.binary = self.subclass(line, line_loc, symbolics)

    def subclass(self, line, line_loc, symbolics):
        """ Defines line type and parses to binary.

            Code parsing can incorrectly succeed for instructions, e.g.:
                'Memory=Address' will return line.binary=='1111110000000000'

        Args:
            line (str): line from asm, usually sanitized.
            line_loc (int): optional line number specification.
            symbolics (symboltable): optional reference to symbolic table
                instance.

        Returns:
            type (str): instruction type identification as a_type or c_type.
            binary (str(016b)): binary string of parsed instruction.

        Raises:
            ParseError of 'Unknown'-type when instruction fails all parsing.

        """
        dest, comp, jmp = self.code_parse(line)
        if line[0] == "@":  # Address type instruction
            return 'a_type', self.address_parse(line[1:], line_loc, symbolics)
        elif comp:  # Calculation type instruction
            return 'c_type', comp + dest + jmp
        # Following cases cover some poor entry line sanitization
        elif line[0] == '(' and line[-1] == ')':
            return None, ''
        elif line == '':
            return None, ''
        else:
            raise ParseError(line, line_loc)
            return None, ''

    def address_parse(self, line, line_loc, symbolics):
        """ Parses address to binary value.

            Resolves integer address to binary. If string and not in
            symboltable class resolves to a new key, otherwise returns found
            value.

        Args:
            line (str): line identified with @ as first character.
                Can contain any characters, (usually) with whitespace and
                comments removed.
            line_loc (int): specifies line number. Accepts None.
            symbolics (symboltable): reference to symbolic table instance.
                Accepts None.

        Returns:
            binary (str(016b)): binary valued string of resolved address.

        Raises:
            ParseError when given a variable address with no symboltable.

        """
        try:
            binary = format(int(line), '016b')
        except ValueError:
            if symbolics is not None:
                binary = symbolics.resolve(line)
            else:
                raise ParseError(line, self.line_loc, type="a-type")
                binary = None
        return binary

    def code_parse(self, line):
        """Translates C-command type to binary representation.

            Does not raise errors with failed parse, comp is not None
            identifies succesful parse.

            comp + dest + jmp creates a valid hack (016b) instruction.

        Args:
            line (str): Any string with possible c-type parsing.
                Can contain any characters, (usually) with whitespace and
                comments removed. Prefers sanitized strings.

        Returns:
            dest (str(010b)): binary representation of parsed destination
            comp (str(03b)): binary representation of parsed computation
            jmp (str(03b)): binary representation of parsed jump

        """

        # Regular expression parsing, with longer matches first
        # Re always succeeds at finding the matching instruction
        _re_comp = (r"(D\|A|D&A|A-D|D-A|D\+A|A-1|D-1|A\+1|D\+1|"
                    r"D\|M|D&M|M-D|D-M|D\+M|M-1|M\+1|-M|!M|M|"
                    r"-A|-D|!A|!D|A|D|-1|1|0?)")
        _re_dest = r"((AMD|AD|AM|MD|A|M|D)=)?"
        _re_jmp = r"(;(JGT|JEQ|JGE|JLT|JNE|JLE|JMP))?"

        _re_line = re.compile('{0}{1}{2}'.format(_re_dest, _re_comp, _re_jmp))

        grouped_c = re.match(_re_line, line)

        # C-command parsing dictionaries:
        comp_table = {
            '0': '1110101010', '1': '1110111111', '-1': '1110111010',
            'D': '1110001100', 'A': '1110110000', '!D': '1110001101',
            '!A': '1110110001', '-D': '1110001111', '-A': '1110110011',
            'D+1': '1110011111', 'A+1': '1110110111', 'D-1': '1110001110',
            'A-1': '1110110010', 'D+A': '1110000010', 'D-A': '1110010011',
            'A-D': '1110000111', 'D&A': '1110000000', 'D|A': '1110010101',
            'M': '1111110000', '!M': '1111110001', '-M': '1111110011',
            'M+1': '1111110111', 'M-1': '1111110010', 'D+M': '1111000010',
            'D-M': '1111010011', 'M-D': '1111000111', 'D&M': '1111000000',
            'D|M': '1111010101'
        }

        dest_table = {
            'None': '000', 'M': '001', 'D': '010', 'MD': '011',
            'A': '100', 'AM': '101', 'AD': '110', 'AMD': '111'
        }

        jmp_table = {
            'None': '000', 'JGT': '001', 'JEQ': '010', 'JGE': '011',
            'JLT': '100', 'JNE': '101', 'JLE': '110', 'JMP': '111'
        }

        # Parse according to dictionaries
        dest = dest_table[str(grouped_c.group(2))]
        if grouped_c.group(3):
            comp = comp_table[str(grouped_c.group(3))]
        else:
            comp = None
        jmp = jmp_table[str(grouped_c.group(5))]

        return dest, comp, jmp


class symboltable(object):
    """ Maintains symbolic table of true label locations.

    Attributes:
        lines (list of str): List of (sanitized) commands with comments, empty
            lines and spaces removed. Can be directly parsed.
        table (dict of str: str(016b)): Dictionary of pre-initialized symbolic
            label values.
        used (int): Number of registries used, including 0-registry.

    Todo:
        *Check for exceeding memory space for variables, exception
    """

    def __init__(self, lines):
        self.lines = self._sanitizeasm(lines)
        self.table = self.inittable(self.lines)

    def __getitem__(self, i):
        """ Defines instance[symbolic key] syntax for class """
        return self.table[i]

    def resolve(self, label):
        """ Resolves label by returning dictionary value or creating new key.

            New keys are assigned binary valued addresses after pre-assigned
            register values (starting from register 16).

        Args:
            label (str): Symbolic label or variable to resolve.

        Returns:
            binary (str(016b)): Resolved binary valued address.

        """
        try:
            binary = self.table[label]
        except KeyError:
            self.used += 1
            self.table[label] = format(int(self.used), '016b')
            binary = self.table[label]
        return binary

    @staticmethod
    def _sanitizeasm(lines):
        """ Fully sanitizes all lines, removing leftover empty lines. """
        sane_lines = []
        for line in lines:
            sane_line = _sanitizeline(line)
            if sane_line:
                sane_lines.append(sane_line)
        return sane_lines

    def inittable(self, lines):
        """ Initializes symbolic table with pre-set values and asm labels.

        Args:
            lines (list of str): list of fully sanitized asm instructions.

        Returns:
            table (dict): Dictionary with label|variable: address pairs.

        """
        table = {'R' + str(i): format(i, '016b') for i in range(16)}
        table['SP'] = format(0, '016b')
        table['LCL'] = format(1, '016b')
        table['ARG'] = format(2, '016b')
        table['THIS'] = format(3, '016b')
        table['THAT'] = format(4, '016b')
        table['SCREEN'] = format(16384, '016b')
        table['KBD'] = format(24576, '016b')

        self.used = 15  # pre-used registers 0-15

        c_idx = 0
        c_lines = []
        for i, line in enumerate(lines):
            if line[0] == '(' and line[-1] == ')':
                table[line[1:-1]] = format(c_idx, "016b")
            else:
                c_idx += 1
                c_lines.append(i)

        c_list = []
        for c_line in c_lines:
            c_list.append(lines[c_line])
        self.lines = c_list

        return table


class ParseError(Exception):
    """ Exception raised for failed parse.

    Outputs to log-file in working directory
    """

    def __init__(self, line, line_loc, path='./log.txt', itype='Unknown'):
        self.line = line
        self.line_loc = line_loc
        self.type = type
        self.printlog(line, line_loc, path, itype)
        self.path = path

    def printlog(self, line, line_loc, path, itype):
        """ Prints log-file """
        with open(path, 'w') as log:
            print("{2} Error parsing {0}: {1}".format(line_loc, line, itype),
                  file=log)


class InputError(Exception):
    """ Exception raised for improper file input """

    def __init__(self, file, message):
        self.file = file
        self.message = message


def _sanitizeline(line):
    """ Sanitizes input asm lines by removing all whitespace and comments """
    line = re.sub(r'\s', '', re.split(r'//', line)[0])
    return line


def main(asmfile, outputdir=None):
    """ Creates a symbolictable isntance and parseline instances.

        Holds asm in memory while reading and hack while writing.
        All parseline objects along with symbolic table are retained and
        returned for ease of error handling. To avoid (possibly) large memory
        footprint function can be written inside loop to facilitate garbage
        collection and parseline instances discarded, but symboltable needs
        to be adjusted to disgard sanitized lines.

        parseline instances do not require strong sanitization.

        (Assumes relatively small file sizes for input and output).

    Args:
        asmfile (str): Filepath to input asm.
        outputdir (str): Optional filepath to output hack. If empty output is
            placed in input directory.

    Returns:
        parsed (list of parseline): Instances of parsed instruction lines
        symbolics (symbolictable): Filled instance of the instruction symbolics

        """
    lines = [line.strip() for line in open(asmfile)]
    symbolics = symboltable(lines)

    line_loc = 0
    parsed = []
    for line in symbolics.lines:
        line_loc += 1
        try:
            parsed.append(parseline(line, line_loc, symbolics))
        except ParseError as err:
            print("{2} Error parsing {0}: {1}".format(err.line_loc, err.line,
                                                      err.type))

    if outputdir is None:  # Use asm filepath to create hackfile
        hackfile = re.sub(r'(asm)$', 'hack', asmfile)
    else:
        hackfile = outputdir + os.path.splitext(os.path.split(asmfile)[1])[0]\
            + '.hack'

    with open(hackfile, 'w') as destfile:
        for line in parsed:
            print(line.binary, file=destfile)

    # Returns for error handling
    return parsed, symbolics


if __name__ == "__main__":
    # Utility config
    # Called from commandline with optional destination path:
    #    'python assembler.py "path-to.asm" -d "path-to.hack"'
    parser = argparse.ArgumentParser(description='Parse a hack assembly file '
                                     'to machine code.')
    parser.add_argument('filepath', type=str, help='path to source asm')
    parser.add_argument('--destination', '-d', type=str, default=None,
                        metavar='OUTPUTDIR',
                        help='output directory, by default uses asm path')
    args = parser.parse_args()

    if os.path.splitext(args.filepath)[1] != '.asm':
        raise InputError(args.filepath, "Not an asm-file")

    if args.destination:
        if args.destination[-1:] != '\\':
            destdir = args.destination + '\\'
        else:
            destdir = args.destination
    else:
        destdir = args.destination

    # Main function calls
    main(args.filepath, destdir)
    print('Assembly complete!')
