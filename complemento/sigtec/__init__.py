def classFactory(iface):
    from .plugin import SigtecPlugin
    return SigtecPlugin(iface)
