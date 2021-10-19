from os import SEEK_END


def readlast(f, sep='\n', fixed=True):
    r"""Read the last segment from a file-like object.

    :param f: File to read last line from.
    :type  f: file-like object
    :param sep: Segment separator (delimiter).
    :type  sep: bytes, str
    :param fixed: Treat data in ``f`` as a chain of fixed size blocks.
    :type  fixed: bool
    :returns: Last line of file.
    :rtype: bytes, str
    """
    bs = len(sep)
    step = bs if fixed else 1
    if not bs:
        raise ValueError("Zero-length separator.")
    try:
        o = f.seek(0, SEEK_END)
        o = f.seek(o - bs - step)  # - Ignore trailing delimiter 'sep'.
        while f.read(bs) != sep:  # - Until reaching 'sep': Read sep-sized block
            o = f.seek(o - step)  # and then seek to the block to read next.
    except (OSError, ValueError):  # - Beginning of file reached.
        f.seek(0)
    return f.read()


def test_readlast():
    from io import BytesIO, StringIO

    # Text mode.
    f = StringIO("first\nlast\n")
    assert readlast(f, "\n") == "last\n"

    # Bytes.
    f = BytesIO(b'first|last')
    assert readlast(f, b'|') == b'last'

    # Bytes, UTF-8.
    f = BytesIO("X\nY\n".encode("utf-8"))
    assert readlast(f, b'\n').decode() == "Y\n"

    # Bytes, UTF-16.
    f = BytesIO("X\nY\n".encode("utf-16"))
    assert readlast(f, b'\n\x00').decode('utf-16') == "Y\n"

    # Bytes, UTF-32.
    f = BytesIO("X\nY\n".encode("utf-32"))
    assert readlast(f, b'\n\x00\x00\x00').decode('utf-32') == "Y\n"

    # Multichar delimiter.
    f = StringIO("X<br>Y")
    assert readlast(f, "<br>", fixed=False) == "Y"

    # Make sure you use the correct delimiters.
    seps = {'utf8': b'\n', 'utf16': b'\n\x00', 'utf32': b'\n\x00\x00\x00'}
    assert "\n".encode('utf8') == seps['utf8']
    assert "\n".encode('utf16')[2:] == seps['utf16']
    assert "\n".encode('utf32')[4:] == seps['utf32']

    # Edge cases.
    edges = (
        # Text , Match
        ("", ""),  # Empty file, empty string.
        ("X", "X"),  # No delimiter, full content.
        ("\n", "\n"),
        ("\n\n", "\n"),
        # UTF16/32 encoded U+270A (b"\n\x00\n'\n\x00"/utf16)
        (b'\n\xe2\x9c\x8a\n'.decode(), b'\xe2\x9c\x8a\n'.decode()),
    )
    for txt, match in edges:
        for enc, sep in seps.items():
            assert readlast(BytesIO(txt.encode(enc)), sep).decode(enc) == match
