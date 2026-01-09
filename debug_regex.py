import re

log_text = """
[GNB_APP]   pdsch_AntennaPorts N1 2 N2 1 XP 2 pusch_AntennaPorts 4
Assertion (num_tx >= config.pdsch_AntennaPorts.XP * config.pdsch_AntennaPorts.N1 * config.pdsch_AntennaPorts.N2) failed!
In RCconfig_nr_macrlc() ../../../openair2/GNB_APP/gnb_config.c:1502
"""

patterns = [
    r"Assertion.*failed",
    r"Segmentation fault",
    r"dumping core",
    r"exiting with status 1",
    r"AS_ASSERT"
]

print(f"Testing text length: {len(log_text)}")

for pattern in patterns:
    match = re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE)
    print(f"Pattern '{pattern}': {match}")
