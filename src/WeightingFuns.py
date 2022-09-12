def default(iteration, pos):
    diff = 1.5 + pos * 2
    return 1 / (diff ** iteration)