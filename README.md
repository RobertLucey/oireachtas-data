Oireachtas Data
===============

Tools and data to work with data from the oireachtas api a bit easier.

Currently only provides data for debates since that's interesting. Will add other things if I have the time and energy.

Also parses data not given through the api but is included in the PDF of the minutes. For some reason a lot of debate sections are forbidden.

Installation
------------

`pip install oireachtas_data`

Dependencies
------------

Poppler - `sudo apt install libpoppler-cpp-dev`
PDFToHTML - `sudo apt install pdftohtml`

Usage
-----

From the repo after running `make setup` to download and parse all the debates (or as much as you like) run `make pull_debates`. Once you have enough downloaded you can run `make load_debates` where you will be dropped into a debugger with a variable `debates` which you can work with


Caveats
-------

The API often denies access to resources so content is parsed from the PDF of the minutes. This can make it so metadata isn't included everywhere and sometimes (though rarely) the parsing of speech segments and the associated speaker isn't correct
