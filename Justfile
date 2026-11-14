run *ARGS:
    python3 -m muni_board {{ARGS}}

live:
    python3 -m muni_board --matrix

test:
    python3 -m unittest discover -s tests -v

check:
    python3 -m compileall -q muni_board device tests tools

verify: test check
