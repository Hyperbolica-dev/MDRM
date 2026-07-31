import sys
sys.path.append('/home/user/dev/projects/RCS')
from model.dynamics import prc_shift, calculate_sleep_debt

wake_target_hour = 8.5
sleep_need = 7.0
lambda_d = 0.9
recovery_k = 0.4
recovery_tau = 2.0
target_m = wake_target_hour - sleep_need / 2.0
deadband = 0.5
max_offset = 3.0
days = 7


def fold(hours):
    while hours > 12:
        hours -= 24
    while hours < -12:
        hours += 24
    return hours


def simulate(initial_p, initial_d, apply_light, natural_drift):
    p, d = initial_p, initial_d
    traj = [(0, p, d)]
    for day in range(1, days + 1):
        msm = target_m + p
        cbt_min = fold(msm + 1.5)
        shift = 0.0
        if apply_light:
            if p > deadband:
                scale = min(1.0, (p - deadband) / 2.0)
                offset = max_offset * scale
                shift = prc_shift(cbt_min, cbt_min + offset)
            elif p < -deadband:
                scale = min(1.0, (abs(p) - deadband) / 2.0)
                offset = max_offset * scale
                shift = prc_shift(cbt_min, cbt_min - offset)
        p = p + shift + natural_drift * p
        p = fold(p)
        sleep_actual = sleep_need + min(2.0, 0.3 * d)
        d = calculate_sleep_debt(d, sleep_actual, sleep_need, lambda_d, recovery_k, recovery_tau)
        traj.append((day, p, d))
    return traj


def report(label, traj):
    print(label)
    for day, p, d in traj:
        marker = ""
        if abs(p) <= 1.0 and d <= 2.0:
            marker = " *"
        print(f"day {day}  P={p:6.2f}  D={d:6.2f}{marker}")
    converged = next((day for day, p, d in traj if abs(p) <= 1.0 and d <= 2.0), None)
    if converged is not None:
        print(f"converged day {converged}")
    else:
        print("not converged in window")
    print()


s1 = simulate(3.0, 4.0, True, 0.0)
s2 = simulate(-3.0, 6.0, True, 0.0)
s3 = simulate(3.0, 4.0, False, -0.1)

report("Scenario 1: Social Jetlag (P=+3.0, D=4.0) morning light", s1)
report("Scenario 2: Severe Deprivation (P=-3.0, D=6.0) evening light", s2)
report("Scenario 3: Control (P=+3.0, D=4.0) no light", s3)
