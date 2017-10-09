# @author Huseyin Alecakir
# @date   09.16.2017
import random
import math

# seed
seed_num = 13
random.seed(seed_num)

# global constants for simulated data
num_student = None
num_question = None
num_kc = None


knowledge_components = set()

last = dict()  # number of the last attempt done by student
question = dict()  # question done by Student S at attempt A
answer = dict()  # correctness of the answer given by Student S at attempt A

initial_mastery = dict()  # includes initial mastery for each of the KCs
learn = dict()  # learning parameter for each KC
slip = dict()  # slipping parameter for each question
guess = dict()  # guessing parameter for each question
q_matrix = dict()  # includes KCs required for answering a question

# saved parameters
s_initial_mastery = dict()
s_learn = dict()
s_slip = dict()
s_guess = dict()


def simulated_data():
    global num_student, num_question, num_kc
    global initial_mastery, learn, guess, slip, last, question, answer, q_matrix

    num_student = 10
    num_question = 100
    num_kc = 20

    initial_mastery = {n: 0 for n in range(1, num_kc + 1)}
    learn = {n: 0 for n in range(1, num_kc + 1)}
    guess = {n: 0 for n in range(1, num_question + 1)}
    slip = {n: 0 for n in range(1, num_question + 1)}

    last = {n: random.randint(10, num_question - 1) for n in range(1, num_student + 1)}

    for student in last:
        question_sample = [i for i in sorted(random.sample(range(1, num_question + 1), last[student]))]
        question[student] = {}
        answer[student] = {}
        for attempt, _question in zip(range(1, last[student] + 1), question_sample):
            question[student][attempt] = _question
            answer[student][attempt] = random.randint(0, 1)

    q_matrix = {}
    for _question in range(1, num_question + 1):
        kc_number = random.randint(1, num_kc)
        question_sample = [i for i in sorted(random.sample(range(1, num_kc + 1), kc_number))]
        q_matrix[_question] = question_sample

    for kc in range(1, num_kc+1):
        knowledge_components.add(kc)


def read_real_data(file_name):
    global initial_mastery, learn, guess, slip, last, question, answer, q_matrix
    input_data = open(file_name, "r")
    for line in input_data:
        fields = line.split("\t")
        answer_s = int(fields[0])
        student_id = fields[1]
        question_id = fields[2]
        skills = fields[3].split("~")
        if student_id in last:
            last[student_id] += 1
        else:
            question[student_id] = dict()
            answer[student_id] = dict()
            last[student_id] = 1
        question[student_id][last[student_id]] = question_id
        answer[student_id][last[
            student_id]] = answer_s - 1  # Yudelson uses 2 for correct answer and 1 for incorrect. So we subtract 1 to work with our code
        if question_id not in q_matrix:
            q_matrix[question_id] = skills
            # update knowledge components set
            for kc in skills:
                knowledge_components.add(kc)

    initial_mastery = {n: 0 for n in knowledge_components}
    learn = {n: 0 for n in knowledge_components}
    guess = {n: 0 for n in q_matrix.keys()}
    slip = {n: 0 for n in q_matrix.keys()}


def fill_parameters_randomly():
    # initial mastery and learn
    for i in knowledge_components:
        initial_mastery[i] = random.uniform(0.05, 0.95)
        learn[i] = random.uniform(0.05, 0.5)
    # slip and guess
    for i in q_matrix.keys():
        slip[i] = random.uniform(0.05, 0.45)
        guess[i] = random.uniform(0.01, 0.5)


def filling_forward():
    forward = {}
    for student in last.keys():
        forward[student] = {}
        for kc in knowledge_components:
            forward[student][kc] = {}
            forward[student][kc][1] = initial_mastery[kc]
        for attempt in range(1, last[student]):
            q = question[student][attempt]
            kcs = q_matrix[q]
            nxt = attempt + 1
            for kc in knowledge_components:
                forward[student][kc][nxt] = forward[student][kc][attempt]
            ok = 1.0
            for kc in kcs:
                ok = ok * forward[student][kc][attempt]
            x = ok * (1 - (slip[q] + guess[q]))
            y = guess[q]
            if answer[student][attempt] == 0:
                y = (1 - y)
                x = -x
            for kc in kcs:
                try:
                    forward[student][kc][nxt] = (y * forward[student][kc][attempt] + x) / (y + x)
                except ZeroDivisionError:
                    forward[student][kc][nxt] = (y * forward[student][kc][attempt] + x) / 0.001
            se = 1.0
            for kc in kcs:
                se *= forward[student][kc][nxt] + (1 - forward[student][kc][nxt]) * learn[kc]
            for kc in kcs:
                z = (1 - forward[student][kc][nxt]) * learn[kc]
                try:
                    forward[student][kc][nxt] += se * z / (forward[student][kc][nxt] + z)
                except ZeroDivisionError:
                    forward[student][kc][nxt] += se * z / 0.001
    return forward


def filling_backward(forward):
    backward = {}
    for student in last.keys():
        backward[student] = {}
        for kc in knowledge_components:
            backward[student][kc] = {}
            backward[student][kc][last[student] + 1] = forward[student][kc][last[student]]

        for attempt in range(last[student], 0, -1):
            q = question[student][attempt]
            kcs = q_matrix[q]
            se = 1.0
            for kc in kcs:
                se *= backward[student][kc][attempt + 1]
            for kc in kcs:
                x = learn[kc] * se
                backward[student][kc][attempt] = (backward[student][kc][attempt + 1] - x) / (1 - x)
            ok = 1.0
            for kc in kcs:
                ok *= backward[student][kc][attempt]
            x = ok * (1 - (slip[q] + guess[q]))
            y = guess[q]
            if answer[student][attempt] == 0:
                y = (1 - y)
                x = -x
            for kc in knowledge_components:
                if kc in kcs:
                    backward[student][kc][attempt] = (y * backward[student][kc][attempt] + x) / (y + x)
                else:
                    backward[student][kc][attempt] = backward[student][kc][attempt + 1]
    return backward


def estimate_kc_mastery():
    forward = filling_forward()
    backward = filling_backward(forward)
    best = {}
    for student in last.keys():
        best[student] = {}
        for kc in knowledge_components:
            best[student][kc] = {}
            for attempt in range(1, last[student] + 1):
                best[student][kc][attempt] = forward[student][kc][attempt] * backward[student][kc][attempt]
    return best


def update_slips_and_guess(best):
    for _question in q_matrix.keys():
        slip_numerator = 0.0
        guess_numerator = 0.0
        denominator = 0.0
        for student in last.keys():
            for attempt in range(1, last[student] + 1):
                if _question == question[student][attempt]:
                    ok = 1.0
                    for kc in q_matrix[_question]:
                        ok *= best[student][kc][attempt]
                    denominator += 1
                    if answer[student][attempt] == 1:
                        guess_numerator += 1 - ok
                    else:
                        slip_numerator += ok
        slip[_question] = slip_numerator / denominator
        guess[_question] = guess_numerator / denominator


def update_learn(best):
    for kc in knowledge_components:
        learn_numerator = 0.0
        learn_denominator = 0.0
        for student in last.keys():
            for attempt in range(1, last[student]):
                kcs = q_matrix[question[student][attempt]]
                if kc in kcs:
                    learn_numerator += best[student][kc][attempt + 1] * (1 - best[student][kc][attempt])
                    learn_denominator += 1
        learn[kc] = learn_numerator / learn_denominator


def update_initial_mastery(best):
    for kc in knowledge_components:
        _sum = 0.0
        count = 0
        for student in last.keys():
            _sum += best[student][kc][1]
            count += 1
        initial_mastery[kc] = _sum / count


def calculate_new_parameters(best):
    update_slips_and_guess(best)
    update_learn(best)
    update_initial_mastery(best)


def save_parameters():
    global s_initial_mastery, s_learn, s_guess, s_slip
    s_initial_mastery = {n: initial_mastery[n] for n in initial_mastery}
    s_learn = {n: learn[n] for n in learn}
    s_guess = {n: guess[n] for n in guess}
    s_slip = {n: slip[n] for n in slip}


def calculate_change():
    _max = 0
    m_initial_mastery = max([math.fabs(initial_mastery[i] - s_initial_mastery[i]) for i in initial_mastery])
    m_learn = max([math.fabs(learn[i] - s_learn[i]) for i in learn])
    m_slip = max([math.fabs(slip[i] - s_slip[i]) for i in slip])
    m_guess = max([math.fabs(guess[i] - s_guess[i]) for i in guess])
    if _max < m_initial_mastery:
        _max = m_initial_mastery
    if _max < m_learn:
        _max = m_learn
    if _max < m_guess:
        _max = m_guess
    if _max < m_slip:
        _max = m_slip
    return _max


def climb_once():
    best = estimate_kc_mastery()
    calculate_new_parameters(best)
    return calculate_change()


def measure_prediction_error():
    pass


def train():
    read_real_data("Data/small.txt")
    #simulated_data()
    fill_parameters_randomly()
    save_parameters()
    change = climb_once()
    while change >= 0.1:
        save_parameters()
        change = climb_once()
    pass
    # for climb in range(10):
    #   fill_parameters_randomly()


if __name__ == "__main__":
    train()

