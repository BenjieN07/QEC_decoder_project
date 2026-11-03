from qec_project.workload import encoded_bytes


def test_encoding_includes_frame_and_headers():
    assert encoded_bytes(0,24) == (20,17)
    assert encoded_bytes(2,24) == (20,25)
    assert encoded_bytes(0,25,9) == (22,18)
