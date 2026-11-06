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
