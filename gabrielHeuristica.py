import matplotlib.pyplot as plt
import math
import random
import copy

#Gera as coordenadas dos pontos e as distâncias entre os nós a partir do arquivo .tsp
def dadosTsp(caminhoArquivo):
    coordenadas = {}
    lendoCoordenadas = False
    try:
        with open(caminhoArquivo, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if lendoCoordenadas:
                    if linha == "EOF": break
                    partes = linha.split()
                    nodeID = int(partes[0]) - 1 
                    x, y = int(partes[1]), int(partes[2])
                    coordenadas[nodeID] = (x, y)
                if linha == "NODE_COORD_SECTION": lendoCoordenadas = True
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em {caminhoArquivo}")
        return None, None, None
    
    numNos = len(coordenadas)
    distancias = {}
    for i in range(numNos):
        for j in range(numNos):
                p1 = coordenadas[i]
                p2 = coordenadas[j]
                dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                distancias[(i, j)] = round(dist) 
  
    return numNos, coordenadas, distancias

#Gera os conjuntos de nós (Vb, Vt, Vc, Vo) e o custo mínimo de cobertura por instalação
def gerarDadosCdp(numNos, distancias, fracaoInstalacoes=0.25, fracaoCobertos=0.25, fracaoOpcional=0.5, theta=0.25, usarCustoFixo=True, usarCustoDistancia=False, alfa=0.2):
    depot = 0
    nos = list(range(numNos))
    NC = 7  # clientes atentidos por locker

    nosDisponiveis = [n for n in nos if n != depot]
    numInstalacoes = int(len(nosDisponiveis) * fracaoInstalacoes)
    Vb = nosDisponiveis[:numInstalacoes]

    clientesPotenciais = nosDisponiveis[numInstalacoes:]

    matrizCobertura = {}  # chaves: (cliente, instalacao) -> True, funciona como uma matriz booleana que define quem pode ser atendido por quem
    clientesCobertosPorAlguem = set()

    # Para cada instalação, escolher os NC clientes mais próximos (independente do raio em distancia)
    for instalacao in Vb:
        lista_dist = []
        for cliente in clientesPotenciais:
            d = distancias.get((instalacao, cliente), float('inf'))
            lista_dist.append((d, cliente))
        lista_dist.sort(key=lambda x: x[0])  # 1. Ordenação: do mais próximo para o mais distante.
        mais_proximos = lista_dist[:NC]      # 2. Seleção: Pega os primeiros NC=7 elementos.

        for dist, cliente in mais_proximos:
            matrizCobertura[(cliente, instalacao)] = True
            clientesCobertosPorAlguem.add(cliente)

    Vt = [c for c in clientesPotenciais if c not in clientesCobertosPorAlguem]
    clientesRestantes = sorted(list(clientesCobertosPorAlguem))
    numCobertosObrigatorios = int(len(clientesRestantes) * fracaoCobertos)
    Vc = clientesRestantes[:numCobertosObrigatorios]
    Vo = clientesRestantes[numCobertosObrigatorios:]
    Va = Vt + Vc + Vo

    #  valor otimo TSP para eil51
    OPT_TSP = 426    
    
    #numero de clientes
    nC=len(Va)

    #numero de lockers
    nL=len(Vb)

    # dicionário (uma matriz de custos) que armazena o custo para que um cliente seja atendido por um locker
    CUSTO_CLIENTE_LOCKER = {}

    valor_fixo = max(1, int(theta * (OPT_TSP / numNos)))  if usarCustoFixo else 0

    # matrizdeCustos [Va][Vb]
    for c in Va:
        for b in Vb:
            if (c, b) in matrizCobertura:
                d = distancias[(c, b)]
                # Custo Variável (Baseado na Distância)
                valor_distancia = int(alfa * d) if usarCustoDistancia else 0
                
                # Custo final é a soma dos componentes escolhidos
                CUSTO_CLIENTE_LOCKER[(c, b)] = valor_fixo + valor_distancia
                  
    return depot, Vb, Vt, Vc, Vo, Va, matrizCobertura, CUSTO_CLIENTE_LOCKER

#calcula menor incremento de custo ao inserir o vértice v na rota
def calcula_incremento(v, rota, distancias):

    melhor_inc = float("inf")   #infinito
    melhor_pos = None           #posição onde inserir (começa vazio)

    for k in range(len(rota) - 1):    #Percorre todas as posições possíveis na rota de 0 até penúltimo elemento
        i = rota[k]                   #pega o vértice na posição k da rota
        j = rota[k+1]                 #pega o vértice na posição k+1 da rota

        #calcula o custo de inserir v entre i e j
        #Usa distancias.get() para evitar KeyError caso alguma distância esteja faltando, se faltar, o incremento será inf e a posição não será escolhida
        incremento = distancias.get((i, v), float('inf')) \
                    + distancias.get((v, j), float('inf')) \
                    - distancias.get((i, j), float('inf'))


        if incremento < melhor_inc:
            melhor_inc = incremento
            melhor_pos = k + 1

    return melhor_inc, melhor_pos

#usa calcula_incremento para inserir v na melhor posição 
def insercao_mais_barata(v, rota, distancias):
    melhor_inc = float("inf")
    melhor_pos = None

    # testar todas as posições entre cada par consecutivo
    for k in range(len(rota) - 1):
        a = rota[k]
        b = rota[k + 1]

        inc = distancias[(a, v)] + distancias[(v, b)] - distancias[(a, b)]

        if inc < melhor_inc:
            melhor_inc = inc
            melhor_pos = k + 1

    return melhor_inc, melhor_pos

# MÉTODO 1: locker mais próximo que cobre i
def escolher_locker_metodo1(i, VB, distancias, matrizCobertura):
    melhor_b = None
    menor_dist = float("inf")

    for b in VB:
        if (i, b) in matrizCobertura:
            d = distancias.get((i, b), float("inf"))
            if d < menor_dist:
                menor_dist = d
                melhor_b = b

    return melhor_b


# MÉTODO 2: locker que minimiza (ci + incremento) e cobre mais clientes
def escolher_locker_metodo2(i, VB, distancias, matrizCobertura, rota, ClientesAtendidosLocker, CUSTO_CLIENTE_LOCKER):
    melhor_b = None
    melhor_score = float("inf")
    melhor_inc_b = float("inf")

    # Clientes já cobertos 
    clientes_ja_cobertos = set()
    for lista in ClientesAtendidosLocker.values():
        clientes_ja_cobertos.update(lista)

    # analisar cada locker
    for b in VB:

        # 1. Só pode escolher se esse PL cobre i
        if (i, b) not in matrizCobertura:
            continue
        
        # O Custo ci do cliente que está sendo avaliado (termo constante na comparação)
        custo_ci_cliente = CUSTO_CLIENTE_LOCKER[(i, b)]

        # 2. Incremento se inserir b na rota (Custo de Roteamento)
        if b in rota:
            inc_b = 0
        else:
            inc_b, _ = calcula_incremento(b, rota, distancias)
        
        # O valor monetário de cada cliente extra coberto é o Custo ci
        ganho_monetario = 0
        for (cliente, pl) in matrizCobertura:
            if pl == b and cliente not in clientes_ja_cobertos:
                ganho_monetario += CUSTO_CLIENTE_LOCKER[(cliente, b)]        
        # Score = CUSTO DO PL + CUSTO DO CLIENTE i - GANHO DE COBERTURA EXTRA
        score = inc_b + custo_ci_cliente - ganho_monetario
        
        # Critério de desempate: se scores forem iguais, pega o com menor incremento de rota
        if score < melhor_score or (score == melhor_score and inc_b < melhor_inc_b):
            melhor_score = score
            melhor_inc_b = inc_b
            melhor_b = b

    return melhor_b

def aplicar_2opt(rota, distancias):

    # Garante rota fechada
    if rota[0] != rota[-1]:
        rota = rota + [rota[0]]

    melhor_rota = rota[:]
    estavel = False

    while not estavel:
        estavel = True

        for i in range(1, len(melhor_rota) - 2):
            for j in range(i + 1, len(melhor_rota) - 1):

                a, b = melhor_rota[i-1], melhor_rota[i]
                c, d = melhor_rota[j], melhor_rota[j+1]

                d_atual = distancias[(a, b)] + distancias[(c, d)]
                d_nova  = distancias[(a, c)] + distancias[(b, d)]

                if d_nova < d_atual:
                    melhor_rota = (
                        melhor_rota[:i] +
                        melhor_rota[i:j+1][::-1] +
                        melhor_rota[j+1:]
                    )
                    estavel = False
                    break
            if not estavel:
                break

    nova_dist = sum(
        distancias[(melhor_rota[k], melhor_rota[k+1])]
        for k in range(len(melhor_rota)-1)
    )

    return melhor_rota, nova_dist

def heuristica (VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER,
               usarMetodo2=True):

    rota = [0, 0]
    custo_distancias = 0.0
    custo_lockers = 0.0

    LockerAberto = {b: False for b in VB}
    ClientesAtendidosLocker = {b: [] for b in VB}

    # 1) inserir Vt (devem ser visitados)
    for i in VT:
        inc,pos = insercao_mais_barata(i, rota, distancias)
        rota.insert(pos, i)
        custo_distancias += inc

    # 2) tratar Vc (devem ser cobertos)
    for i in VC:
        if usarMetodo2:
            b_escolhido = escolher_locker_metodo2(i, VB, distancias, matrizCobertura, rota, ClientesAtendidosLocker, CUSTO_CLIENTE_LOCKER)       
        else:
            b_escolhido = escolher_locker_metodo1(i, VB, distancias, matrizCobertura)

        if b_escolhido is None:
            #inc = insercao_mais_barata(i, rota, distancias)
            inc, pos = insercao_mais_barata(i, rota, distancias) 
            rota.insert(pos, i)
            custo_distancias += inc
            continue

        # registrar cliente no locker escolhido
        ClientesAtendidosLocker[b_escolhido].append(i)
        custo_lockers += CUSTO_CLIENTE_LOCKER[(i, b_escolhido)]

        # se abrir o locker, inserir na rota
        if not LockerAberto[b_escolhido]:
            inc,pos = insercao_mais_barata(b_escolhido, rota, distancias)
            rota.insert(pos, b_escolhido)
            custo_distancias += inc
            LockerAberto[b_escolhido] = True


    # 3) tratar VO (opcionais): tentar reaproveitar lockers abertos, senão decidir abrir novo locker vs visitar
    ClientesR = set(VO)
    lista_para_processar = list(ClientesR)

    for i in lista_para_processar:
        # 3A: tentar associar a um locker já aberto
        associado = False
        for b in VB:
            if LockerAberto[b] and (i, b) in matrizCobertura:
                ClientesAtendidosLocker[b].append(i)
                custo_lockers += CUSTO_CLIENTE_LOCKER[(i, b)]
                ClientesR.remove(i)
                associado = True
                break
        if associado:
            continue

        # 3B: se nenhum aberto atende, considerar abrir um novo locker (ou visitar)
        inc_visita, pos_visita = calcula_incremento(i, rota, distancias)
        if usarMetodo2:
            b_candidato = escolher_locker_metodo2(i, VB, distancias, matrizCobertura, rota, ClientesAtendidosLocker, CUSTO_CLIENTE_LOCKER)
        else:
            b_candidato = escolher_locker_metodo1(i, VB, distancias, matrizCobertura)

        melhor_opcao_cobertura = False
        if b_candidato is not None:
            inc_pl, pos_pl = calcula_incremento(b_candidato, rota, distancias)
            custo_cobertura_total = inc_pl + CUSTO_CLIENTE_LOCKER[(i, b_candidato)]

            # comparar com visita direta (inc_visita)
            if custo_cobertura_total < inc_visita:
                # abrir PL, inserir PL e associar cliente
                rota.insert(pos_pl, b_candidato)
                custo_distancias += inc_pl
                LockerAberto[b_candidato] = True
                ClientesAtendidosLocker[b_candidato].append(i)
                custo_lockers += CUSTO_CLIENTE_LOCKER[(i, b_candidato)]
                ClientesR.remove(i)
                melhor_opcao_cobertura = True

        if not melhor_opcao_cobertura:
            # visitar o cliente
            rota.insert(pos_visita, i)
            custo_distancias += inc_visita
            ClientesR.remove(i)

    rota, custo_distancias = aplicar_2opt(rota, distancias)

    custo_total = custo_distancias + custo_lockers
    return rota, custo_total, custo_distancias, custo_lockers, LockerAberto, ClientesAtendidosLocker, ClientesR
   
# Retorna os 7 clientes mais próximos do locker b
def clientes_mais_proximos(b, Va, distancias, k=7):
    dist = []
    for c in Va:
        if (c, b) in distancias:
            dist.append((c, distancias[(c, b)]))

    dist.sort(key=lambda x: x[1])
    return dist[:k]

# Algoritmo Iterated Greedy

def destruir_solucao(rota, ClientesAtendidosLocker, VT, vr=10):
    rota_parcial = rota[:]
    copia_atrib = copy.deepcopy(ClientesAtendidosLocker)
    removidos = []
    i = 0

    while i < vr and len(rota_parcial) > 3:
        opcao = random.choice([0, 1])

        if opcao == 0:
            # Remover um nó da rota (exceto depósito e VT)
            candidatos = [n for n in rota_parcial[1:-1] if n not in VT]
            if candidatos:
                x = random.choice(candidatos)
                rota_parcial.remove(x)
                if x in copia_atrib and len(copia_atrib[x]) > 0:
                    # Removeu um locker: seus clientes ficam órfãos
                    clientes_orfaos = copia_atrib[x][:]
                    removidos.extend(clientes_orfaos)
                    copia_atrib[x] = []
                    i += len(clientes_orfaos)
                else:
                    removidos.append(x)
                    i += 1
        else:
            # Remover um cliente aleatório de algum locker ativo
            lockers_ativos = [b for b, c in copia_atrib.items() if len(c) > 0 and b in rota_parcial]
            if lockers_ativos:
                b = random.choice(lockers_ativos)
                x = random.choice(copia_atrib[b])
                if x not in removidos:
                    copia_atrib[b].remove(x)
                    removidos.append(x)
                    i += 1

    return rota_parcial, list(set(removidos)), copia_atrib
    
def reparar_solucao(rota_parcial, removidos, ClientesAtendidosLocker_atual, VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER):
    rota = rota_parcial[:]
    LockerAberto = {b: (b in rota) for b in VB}
    ClientesAtendidosLocker = copy.deepcopy(ClientesAtendidosLocker_atual)

    # Processar apenas os clientes removidos
    for x in removidos:
        if x in VT or x in VC:
            # Obrigatório: procurar melhor locker; se não achar, inserir na rota
            b = escolher_locker_metodo2(x, VB, distancias, matrizCobertura, rota, ClientesAtendidosLocker, CUSTO_CLIENTE_LOCKER)
            if b is not None:
                ClientesAtendidosLocker[b].append(x)
                if not LockerAberto[b]:
                    _, pos = insercao_mais_barata(b, rota, distancias)
                    rota.insert(pos, b)
                    LockerAberto[b] = True
            else:
                _, pos = insercao_mais_barata(x, rota, distancias)
                rota.insert(pos, x)

        elif x in VO:
            # Opcional: onde fica melhor, rota ou locker?
            # Primeiro tenta locker já aberto
            associado = False
            for b in VB:
                if LockerAberto[b] and (x, b) in matrizCobertura:
                    ClientesAtendidosLocker[b].append(x)
                    associado = True
                    break
            if associado:
                continue

            # Se nenhum aberto atende, comparar abrir novo locker vs visitar direto
            inc_visita, pos_visita = calcula_incremento(x, rota, distancias)
            b_candidato = escolher_locker_metodo2(x, VB, distancias, matrizCobertura, rota, ClientesAtendidosLocker, CUSTO_CLIENTE_LOCKER)

            if b_candidato is not None:
                if b_candidato in rota:
                    inc_pl = 0
                else:
                    inc_pl, pos_pl = calcula_incremento(b_candidato, rota, distancias)
                custo_cobertura_total = inc_pl + CUSTO_CLIENTE_LOCKER[(x, b_candidato)]

                if custo_cobertura_total < inc_visita:
                    if not LockerAberto[b_candidato]:
                        _, pos_pl = insercao_mais_barata(b_candidato, rota, distancias)
                        rota.insert(pos_pl, b_candidato)
                        LockerAberto[b_candidato] = True
                    ClientesAtendidosLocker[b_candidato].append(x)
                else:
                    rota.insert(pos_visita, x)
            else:
                rota.insert(pos_visita, x)

    # Limpeza final e atualização de custos
    rota, custo_dist = aplicar_2opt(rota, distancias)
    custo_l = sum(CUSTO_CLIENTE_LOCKER[(c, b)] for b, lista in ClientesAtendidosLocker.items() for c in lista)

    return rota, (custo_dist + custo_l), custo_dist, custo_l, LockerAberto, ClientesAtendidosLocker

def iterated_greedy(VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER, iter_max=100, vr=10):
    # S = Constroi_SoluçãoVálida() + 2_OPT (já incluído na heurística)
    res_inicial = heuristica(VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER)
    melhor_sol = list(res_inicial)  # [rota, custoT, custoD, custoL, LA, At, CR]

    for i in range(iter_max):
        # Destruir sempre a melhor solução (S*)
        rota_p, rem, atrib_p = destruir_solucao(melhor_sol[0], melhor_sol[5], VT, vr)

        # Reconstruir de forma gulosa
        res_n = reparar_solucao(rota_p, rem, atrib_p, VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER)

        # Aceitação gulosa: Se S é melhor que S*, S* = S
        if res_n[1] < melhor_sol[1]:
            melhor_sol = list(res_n) + [[]]
            print(f"Iteração {i}: Novo Melhor Custo Total = {res_n[1]:.2f}")

    return melhor_sol

# plotagem
def plot_cdp_solution(coordenadas, depot, VB, VT, VC, VO, rota,LockerAberto, ClientesAtendidosLocker, distancias, custoTotal, custoDist, custoLockers, nome_arquivo="solucao_heuristica_cdp2.png"):

    plt.figure(figsize=(12, 8))
   
    for b, clientes in ClientesAtendidosLocker.items():
            if LockerAberto.get(b, False): # Só desenha elos se o locker estiver na rota
                xb, yb = coordenadas[b]
                for c in clientes:
                    xc, yc = coordenadas[c]
                    # Desenha o elo de cobertura real (azul pontilhado)
                    plt.plot([xb, xc], [yb, yc],
                            color='blue', linewidth=0.8, linestyle=':', alpha=0.6, zorder=2)
                    
                    # Desenha um círculo em volta do locker que engloba seus clientes atendidos
                    dist_atendidos = [distancias[(c, b)] for c in clientes]
                    if dist_atendidos:
                        raio_dinamico = max(dist_atendidos)
                        circle = plt.Circle((xb, yb), raio_dinamico, color='blue', fill=False,
                                            linestyle='--', alpha=0.5)
                        plt.gca().add_artist(circle)        
    
    clientes_vazios = [c for c in VC] + [c for c in VO]
    clientes_vazios_coords = [coordenadas[c] for c in clientes_vazios if c in coordenadas]
    if clientes_vazios_coords:
        vazio_x, vazio_y = zip(*clientes_vazios_coords)
        plt.plot(vazio_x, vazio_y, marker='o', color='white', markersize=8, markeredgecolor='gray', linestyle='', zorder=3)

    Vb_coords = [coordenadas[b] for b in VB if b in coordenadas]
    if Vb_coords:
        Vb_x, Vb_y = zip(*Vb_coords)
        plt.plot(Vb_x, Vb_y, marker='s', color='gray', markersize=10, linestyle='', zorder=3)

    Vt_coords = [coordenadas[t] for t in VT if t in coordenadas]
    if Vt_coords:
        Vt_x, Vt_y = zip(*Vt_coords)
        plt.plot(Vt_x, Vt_y, marker='o', color='black', markersize=8, linestyle='', zorder=4)

    depot_coord = coordenadas[depot]
    plt.plot(depot_coord[0], depot_coord[1], marker='D', color='black', markersize=10, linestyle='', zorder=5)

    if rota and len(rota) > 1:
        rota_plot = rota + [rota[0]] 
        rota_coords_plot = [coordenadas[n] for n in rota_plot if n in coordenadas]
        
        rota_x, rota_y = zip(*rota_coords_plot)
        plt.plot(rota_x, rota_y, 'k-', linewidth=2, label='Route', zorder=4, alpha=0.7) 
        plt.plot(rota_x, rota_y, 'o', color='black', markersize=5, zorder=5)

    for i, (x, y) in coordenadas.items():
         plt.text(x, y + 0.5, str(i), fontsize=8, ha='center', color='black')
    
    for i, (x, y) in coordenadas.items():
         plt.text(x, y + 0.5, str(i), fontsize=8, ha='center', color='black') 

    title_text = f"Heurística CDP | Custo Total = {custoTotal:.2f} (Distância: {custoDist:.2f}, Locker: {custoLockers:.2f})"
    plt.title(title_text)   
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    final_handles = []
    final_labels = []
    
    final_handles.append(plt.Line2D([0], [0], marker='D', color='w', label='Depot', markerfacecolor='black', markersize=10))
    final_labels.append('Depot')
    final_handles.append(plt.Line2D([0], [0], marker='s', color='w', label='Facility (Vb)', markerfacecolor='gray', markersize=10))
    final_labels.append('Facility (Vb)')
    final_handles.append(plt.Line2D([0], [0], marker='o', color='w', label='Node must be visited (Vt)', markerfacecolor='black', markersize=8))
    final_labels.append('Node must be visited (Vt)')
    final_handles.append(plt.Line2D([0], [0], marker='o', color='w', label='Node visited or covered (Vc/Vo)', markerfacecolor='white', markeredgecolor='gray', markersize=8))
    final_labels.append('Node visited or covered (Vc/Vo)')
    final_handles.append(plt.Line2D([0], [0], color='black', linewidth=2, label='Route'))
    final_labels.append('Route')
    
    final_handles.append(
    plt.Line2D([0], [0], color='blue', linestyle=':', linewidth=1,
               label='Coverage: 7 nearest clients')
    )
    final_labels.append('Coverage: 7 nearest clients')

    plt.legend(final_handles, final_labels, bbox_to_anchor=(1.03, 1), loc='upper left')
    
    plt.axis('equal') 
    plt.tight_layout(rect=[0, 0, 0.85, 1]) 
    
    plt.savefig(nome_arquivo)
    print(f"Gráfico da solução salvo em '{nome_arquivo}'")


if __name__ == "__main__":
    arquivo = "../tsp/eil51.tsp" 
    
    R_COBERTURA = 12
    FRACAO_INSTALACOES = 0.25
    FRACAO_COBERTOS = 0.25 
    FRACAO_OPCIONAIS = 0.50
    THETA = 0.25
    ALFA = 0.2    
    USAR_FIXO = True
    USAR_DISTANCIA = False

    print(f"Iniciando Heurística CDP para {arquivo}")
    print(f"Parâmetros: R={R_COBERTURA}, Vb={FRACAO_INSTALACOES*100}%, Vc/Vo={FRACAO_COBERTOS*100}%")
    
    numNos, coordenadas, distancias = dadosTsp(arquivo)
    
    if numNos is not None:
        
        depot, VB, VT, VC, VO, VA, matrizCobertura, CUSTO_CLIENTE_LOCKER = gerarDadosCdp(
            numNos, 
            distancias,
            fracaoInstalacoes=FRACAO_INSTALACOES,
            fracaoCobertos=FRACAO_COBERTOS,
            fracaoOpcional=FRACAO_OPCIONAIS,
            theta=THETA,
            alfa=ALFA,
            usarCustoFixo=USAR_FIXO,
            usarCustoDistancia=USAR_DISTANCIA
        )
        
        # 1. Executa Heurística Inicial para ter uma base de comparação
        res_h = heuristica(VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER)
        r_h, cT_h, cD_h, cL_h, LA_h, At_h, _ = res_h
        print(f"Heurística Inicial. Custo Total: {cT_h:.2f}")

        # 2. Executa o Iterated Greedy (IG)
        print("\nIniciando Iterated Greedy...")
        melhor_sol_ig = iterated_greedy(VT, VC, VO, VB, distancias, matrizCobertura, CUSTO_CLIENTE_LOCKER)

        # 3. Desempacota os resultados do IG
        r_ig, cT_ig, cD_ig, cL_ig, LA_ig, At_ig = melhor_sol_ig[:6]

        # 4. Compara e plota os resultados
        print(f"\n--- RESULTADOS ---")
        print(f"Custo Total ANTES IG: {cT_h:.2f}")
        print(f"Custo Total DEPOIS IG: {cT_ig:.2f}")

        plot_cdp_solution(
            coordenadas, depot, VB, VT, VC, VO,
            r_ig, LA_ig, At_ig, distancias,
            cT_ig, cD_ig, cL_ig,
            nome_arquivo="solucao_IG_REAL.png"
        )

        plot_cdp_solution(
            coordenadas, depot, VB, VT, VC, VO,
            r_h, LA_h, At_h, distancias,
            cT_h, cD_h, cL_h,
            nome_arquivo="solucao_heuristica_cdp2.png"
        )
    else:
        print("Encerrando o script devido a erro na leitura dos dados.")