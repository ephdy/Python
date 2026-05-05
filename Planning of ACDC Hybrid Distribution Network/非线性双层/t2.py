for (mu,epsilon) in [(0,0),(0,1),(1,0),(1,1)]:
    sens = [1 + mu, (1 + mu * 0.1) * (1 - (0.1 + epsilon * 0.1)), (1 + mu * 0.1) * (1 + (0.1 + epsilon * 0.1))]
    print(sens)