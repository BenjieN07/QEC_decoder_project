"""Finite-sample conservative paired interval from two discordant categories."""
from scipy.stats import beta


def exact_interval(count, shots, alpha=.05):
    if shots < 1 or not 0 <= count <= shots:
        raise ValueError('invalid binomial count')
    return (0. if count==0 else float(beta.ppf(alpha/2,count,shots-count+1)),
            1. if count==shots else float(beta.ppf(1-alpha/2,count+1,shots-count)))


def paired_interval(baseline_only, hybrid_only, shots, alpha=.05):
    if baseline_only+hybrid_only > shots:
        raise ValueError('discordant counts exceed shots')
    # Each marginal uses alpha/2; Bonferroni gives >=1-alpha joint coverage.
    if not 0<alpha<1:
        raise ValueError('alpha must lie between 0 and 1')
    a = exact_interval(baseline_only,shots,alpha/2)
    b = exact_interval(hybrid_only,shots,alpha/2)
    return b[0]-a[1],b[1]-a[0]
