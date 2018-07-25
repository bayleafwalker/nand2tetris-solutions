# Nand 2 Tetris Solutions

Based on the course and book by Noam Nisan and Shimon Schocken, available at https://www.nand2tetris.org

## Hardware files

Hardware files are located under \Hardware and implement logic gates and components necessary to build the Hack computer.

## Scripts

assembler.py, under Scripts\ implements an assembler in Python 3 for hack machine language according to the specifications available at https://www.nand2tetris.org/project06

The script can be invoked with 'python assembler.py path_to.asm [-d output_dir\\]'

The assembler in a first pass parses labels in the asm-file to a symbolic table, after which all instructions are parsed to commands. All lines with failed parsing are printed in prompt and logged to working directory log.txt.

The script contains some limited error handling but is not robust against all incorrect instructions. E.g. 'Memory=Address' is parsed as a valid instruction '1111110000000000'.

Scripts\testfiles\ contains compare.bat script invoking Poweshell scripts to assemble Add, Max, MaxL, Pong, PongL, Rect and RectL to Hack and compare against preassembled hack-files. Corresponding asm-files should be placed directly under Scripts\testfiles\asm\ before running test script. Scripts\testfiles\prospective\ contains hack-files assembled with assembler.py, and fully match the preassembled test files. Folder comparison requires rdiff.ps1 by cchamberlain in path or working directory, https://gist.github.com/cchamberlain/883959151aa1162e73f1

