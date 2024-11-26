import networkx as nx
import argparse
import matplotlib.pyplot as plt

class J_maker:
    def __init__(self):
        self.dict = {
        #   r_min r_max, C_min, C_max_ p
            "J15": (20, 20, 2, 3, 1), # j15
            "J23": (20, 20, 3, 4 ,2), # j23
            "J42": (21, 21, 2, 3, 3), # j42
            "J32": (20, 20, 4, 5, 4) # j32
        }

        self.set = set(["J15", "J23", "J42", "J32"])

def make_new_state(J, J_P, A):
    m = len(A)
    A1_min, A1_max = A[0]
    A2_min, A2_max = A[1]
    R_P = J.set.difference(J_P) # The current definition for JLFP

    for Ji in R_P:
        r_min, r_max, C_min, C_max, p_i = J.dict[Ji]
        all_Rx_max = [J.dict[Jx][1] for Jx in R_P]
        rx_max_higher_priority = [J.dict[Jx][1] for Jx in R_P if J.dict[Jx][4] < p_i] 
        ESTi = max(r_min, A1_min)

        t_wc = max(A1_max, min(all_Rx_max, default = 10000))
        t_high = min(rx_max_higher_priority, default = 10000)
        LSTi = min(t_wc, t_high - 1)

        if ESTi <= LSTi:
            EFTi = ESTi + C_min
            LFTi = LSTi + C_max
            PA, CA = [], []
            PA.append(max(ESTi, A2_min))
            PA.append(EFTi)
            CA.append(max(ESTi, A2_max))
            CA.append(LFTi)
            PA.sort()
            CA.sort()
            print(f"Dispatched {Ji}")

            A_copy = A_copy = [(0, 0) for i in range(m)]

            for i in range(m):
                A_copy[i] = (PA[i], CA[i])
                print(f"Availability for core {i}: [{A_copy[i][0]}, {A_copy[i][1]}]")
            
            return Ji, A_copy
        else:
            print(f"Can't dispatch {Ji}")

def collect_released_jobs(J, J_P, PP):
    R_P = set()

    for Ji in J.set.difference(J_P):
        if J.dict[Ji][1] <= PP[1]:
            R_P.add(Ji)
    
    return R_P

def get_R_P(J, J_P, PP):
    R_P = set()    
    R_P = collect_released_jobs(J, J_P, PP)
    
    if len(R_P) == 0: # If set is empty
        all_r_min = [J.dict[Jx][0] for Jx in J.set.difference(J_P)]
        PP = (min(all_r_min), min(all_r_min))
        R_P = collect_released_jobs(J, J_P, PP)
    
    return R_P, PP
 

def make_new_state_ROS(J, J_P, A, PP, EFT, LFT):
    m = len(A)
    A1_min, A1_max = A[0]
    A2_min, A2_max = A[1]
    R_P, PP = get_R_P(J, J_P, PP)

    if len(R_P) == 1:
        PP = A1_min, A1_max

    for Ji in R_P:
        r_min, r_max, C_min, C_max, p_i = J.dict[Ji]
        all_Rx_max = [J.dict[Jx][1] for Jx in R_P]
        rx_max_higher_priority = [J.dict[Jx][1] for Jx in R_P if J.dict[Jx][4] < p_i] 
        ESTi = max(r_min, A1_min)

        t_wc = max(A1_max, min(all_Rx_max, default = 10000))
        t_high = min(rx_max_higher_priority, default = 10000)
        LSTi = min(t_wc, t_high - 1)

        if ESTi <= LSTi:
            EFTi = ESTi + C_min
            LFTi = LSTi + C_max
            EFT.append(EFTi)
            LFT.append(LFTi)
            PA, CA = [], []
            PA.append(max(ESTi, A2_min))
            PA.append(EFTi)
            CA.append(max(ESTi, A2_max))
            CA.append(LFTi)
            PA.sort()
            CA.sort()
            print(f"Dispatched {Ji}")

            A_copy = A_copy = [(0, 0) for i in range(m)]

            for i in range(m):
                A_copy[i] = (PA[i], CA[i])
                print(f"Availability for core {i}: [{A_copy[i][0]}, {A_copy[i][1]}]")
            
            return Ji, A_copy, PP
        else:
            print(f"Can't dispatch {Ji}")

def run(ROS: bool):
    G = nx.DiGraph()
    J = J_maker()
    J_P = set([])

    A = [
        (15, 15), # A1
        (17, 18) # A2
    ]

    if ROS == False:
        PP = (20, 20) # Polling Point interval
        G.add_node(0, name = "Init", A=A)

        for i in range(1, 5):
            print(f"############## State {i + 1} ###############")
            disp_Ji, A = make_new_state(J, J_P, A)
            J_P.add(disp_Ji)
            
            G.add_node(i, name = i, A=A)
            G.add_edge(i - 1, i, job = disp_Ji)
        
        node_labels = {node: f"{data['A']}" for node, data in G.nodes(data=True)}
        edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
        pos = nx.spring_layout(G)  # Generate positions for nodes
        nx.draw(G, pos, with_labels=False, node_color="lightblue", node_size=3000)
        nx.draw_networkx_labels(G, pos, labels=node_labels)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.show()

    if ROS == True:
        PP = (20, 20) # Polling Point interval
        EFT = []
        LFT = []
        G.add_node(0, name = "Init", A=A, PP=PP)

        for i in range(1, 5):
            print(f"############## State {i + 1} ###############")
            disp_Ji, A, PP = make_new_state_ROS(J, J_P, A, PP, EFT, LFT)
            J_P.add(disp_Ji)
            
            G.add_node(i, name = i, A=A, PP=PP)
            G.add_edge(i - 1, i, job = disp_Ji)
        
        # node_labels = {node: f"{data['A']}" for node, data in G.nodes(data=True)}
        node_labels = {node: f"{data['A']} {data['PP']}" for node, data in G.nodes(data=True)}
        edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
        pos = nx.spring_layout(G)  # Generate positions for nodes
        nx.draw(G, pos, with_labels=False, node_color="lightblue", node_size=3000)
        nx.draw_networkx_labels(G, pos, labels=node_labels)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--ROS", action = 'store_true')
    args = parser.parse_args()

    run(args.ROS)