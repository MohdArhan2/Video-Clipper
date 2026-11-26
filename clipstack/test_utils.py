from clipstack.core import Box, ass_time, safe_name, seconds


def test_seconds():
    assert seconds("00:04:34") == 274
    assert seconds("04:34") == 274
    assert seconds("30") == 30
    assert seconds(12.5) == 12.5


def test_ass_time():
    assert ass_time(0) == "0:00:00.00"
    assert ass_time(3661.5) == "1:01:01.50"


def test_safe_name():
    assert safe_name("my clip!") == "my_clip_.mp4"
    assert safe_name("done.mp4") == "done.mp4"


def test_box_crop():
    assert Box(0, 0.4, 0.2, 0.25).crop() == "crop=iw*0.2:ih*0.25:iw*0:ih*0.4"
