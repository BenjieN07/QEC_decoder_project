import pytest
from qec_project import ibm_experiment as experiment


class Service:
    def __init__(self,plan='open',remaining=500,active='test-instance'):
        self.plan=plan;self.remaining=remaining;self.active=active
    def instances(self):return [{'crn':'test-instance','plan':self.plan}]
    def active_instance(self):return self.active
    def usage(self):return {'usage_remaining_seconds':self.remaining}


def test_only_explicit_free_instance_with_allocation_is_accepted(monkeypatch):
    monkeypatch.setattr(experiment,'credentials',lambda:('dummy_token_not_a_real_secret','test-instance'))
    spec={'minimum_free_remaining_seconds':120}
    assert experiment.assert_free(Service(),spec)==500
    for service in (Service(plan='pay-as-you-go'),Service(remaining=60),Service(active='another-instance')):
        with pytest.raises(ValueError):experiment.assert_free(service,spec)


def test_duplicate_job_is_blocked_before_sdk_or_network(tmp_path):
    (tmp_path/'manifest.json').write_text('{}')
    (tmp_path/'job.json').write_text('{}')
    with pytest.raises(ValueError,match='already exists'):experiment.submit(tmp_path)


def test_budget_caps_are_validated_at_submission():
    import copy,json
    from pathlib import Path
    spec=json.loads((Path(__file__).resolve().parents[1]/'configs/ibm_pilot.json').read_text())
    experiment.validate_spec(spec)
    for key,value in [('shots_per_basis',513),('max_execution_time_seconds',61),('minimum_free_remaining_seconds',0)]:
        bad=copy.deepcopy(spec);bad[key]=value
        with pytest.raises(ValueError):experiment.validate_spec(bad)
