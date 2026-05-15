import random

def get_random_exercise_type():
    exercise_types = [
        'choose-words',
        'enter-words',
        # 'order-lines',
        # 'multiple-choice'
    ]

    return random.choice(exercise_types)