from libs.sanitizers import (
    clean_text,
    title_name,
    upper_code,
    clean_gstin,
    clean_phone,
    clean_email,
)


def test_clean_text():
    assert clean_text(None) == ''
    assert clean_text('') == ''
    assert clean_text('   ') == ''
    assert clean_text('  hello   world \t \n test  ') == 'hello world test'


def test_title_name():
    assert title_name(None) == ''
    assert title_name('  jai   prakash ') == 'Jai Prakash'
    assert title_name('GD Foods') == 'GD Foods'
    assert title_name('jai-prakash') == 'Jai-Prakash'
    assert title_name("o'brien") == "O'Brien"
    assert title_name("O'BRIEN") == "O'Brien"
    assert title_name('mcdonald') == 'Mcdonald'


def test_upper_code():
    assert upper_code(None) == ''
    assert upper_code(' gj05ab1234 ') == 'GJ05AB1234'
    assert upper_code('abc-123') == 'ABC-123'


def test_clean_gstin():
    assert clean_gstin(None) == ''
    assert clean_gstin('  27aabcc1408h1zc ') == '27AABCC1408H1ZC'


def test_clean_email():
    assert clean_email(None) == ''
    assert clean_email(' Foo@BAR.com ') == 'foo@bar.com'


def test_clean_phone():
    assert clean_phone(None) == ''
    assert clean_phone(' +91 (987) 654-3210 ') == '+91 987 654 3210'
    assert clean_phone('987-654-3210!') == '987 654 3210'
