from conformance import fitness_token_replay, read_from_file, alpha

log = read_from_file("extension-log.xes")
log_noisy = read_from_file("extension-log-noisy.xes")

mined_model = alpha(log)
print(round(fitness_token_replay(log, mined_model), 5))
print(round(fitness_token_replay(log_noisy, mined_model), 5))