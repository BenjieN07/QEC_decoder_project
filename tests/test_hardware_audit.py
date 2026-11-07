import pytest

from qec_project.hardware_audit import audit, correction_counts


def test_paired_correction_categories():
    result = correction_counts([[1], [0], [1], [0]], [[1], [1], [0], [0]])
    assert [result[k] for k in ('helped', 'hurt', 'both_wrong', 'both_correct')] == [1, 1, 1, 1]
    assert result['decoded_failures'] == result['zero_frame_failures'] == 2
    assert result['decoded_minus_zero_frame_ci'][0] < 0 < result['decoded_minus_zero_frame_ci'][1]
    with pytest.raises(ValueError):
        correction_counts([[0]], [[0], [1]])


def test_public_hardware_replay(tmp_path):
    result = audit('reports/evidence/H1', tmp_path, shots=128)
    for row, failures in zip(result['results'], (242, 165)):
        assert row['replay_verified']
        assert all(row['variants_equal'].values())
        assert row['physical']['decoded_failures'] == failures
        p = row['physical']
        assert p['zero_frame_failures'] - p['helped'] + p['hurt'] == failures
        assert len(row['detectors']) == 24
        assert row['routed_cz'] > row['abstract_cx']
    assert (tmp_path/'detector_activity.png').is_file()
