import pulsectl

pulse = pulsectl.Pulse('test')
print("Outputs:")
for o in pulse.sink_list():
    print(" ", o.name)
print("Inputs:")
for i in pulse.source_list():
    print(" ", i.name)
