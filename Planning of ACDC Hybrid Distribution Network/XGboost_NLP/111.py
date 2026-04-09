a=[0,0.1,0.2]
b=[1,1.2,1.4]
c=set()
for i in a:
    for j in b:
        c.add(1 * j)
        c.add((1-i) * j)
        c.add((1+i) * j)
sorted_list = sorted(c)
print(sorted_list)