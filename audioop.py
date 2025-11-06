"""Stub para ambientes sem o módulo C `audioop`.
Permite que `import audioop` não lance erro quando você não usa recursos de voz.
Se for usar voice/áudio, execute em uma build do Python com audioop nativo.
"""
def __getattr__(name):
    raise NotImplementedError(f"audioop.{name} não suportado neste ambiente")

# Funções comuns podem ser declaradas explicitamente para mensagens de erro mais claras
def lin2lin(*args, **kwargs):
    raise NotImplementedError("audioop.lin2lin não suportado neste ambiente")

def avg(*args, **kwargs):
    raise NotImplementedError("audioop.avg não suportado neste ambiente")