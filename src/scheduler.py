class DistributedScheduler:
    """Selecciona el mejor nodo aplicando la función de aptitud F(i,j)."""
    
    def __init__(self, w1=0.40, w2=0.40, w3=0.10, w4=0.05, w5=0.05):
        self.w1 = w1  # Peso CPU
        self.w2 = w2  # Peso RAM
        self.w3 = w3  # Peso Ancho de banda
        self.w4 = w4  # Peso Reputación
        self.w5 = w5  # Peso Latencia

    def select_best_node(self, peer_table, task):
        # 1. Filtrar nodos ONLINE que cumplan con los requerimientos mínimos
        candidates = []
        for peer in peer_table.values():
            if (peer.status == "ONLINE" and 
                peer.cpu_free >= task.cpu_req and 
                peer.ram_free >= task.ram_req):
                candidates.append(peer)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # 2. Obtener rangos para la normalización Min-Max
        cpus = [c.cpu_free for c in candidates]
        rams = [c.ram_free for c in candidates]
        
        c_min, c_max = min(cpus), max(cpus)
        m_min, m_max = min(rams), max(rams)

        best_node = None
        best_score = -1.0

        # 3. Evaluar cada candidato con la fórmula
        for node in candidates:
            c_norm = (node.cpu_free - c_min) / (c_max - c_min) if c_max > c_min else 1.0
            m_norm = (node.ram_free - m_min) / (m_max - m_min) if m_max > m_min else 1.0
            
            b_norm = 1.0  # Ancho de banda relativo simulación
            r_val = 1.0   # Reputación
            l_norm = 1.0  # Latencia normalizada

            # Cálculo de la función de aptitud
            score = (self.w1 * c_norm + 
                     self.w2 * m_norm + 
                     self.w3 * b_norm + 
                     self.w4 * r_val + 
                     self.w5 * l_norm)

            if score > best_score:
                best_score = score
                best_node = node

        return best_node