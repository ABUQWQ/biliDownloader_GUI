class FNVAL_PRESET:
    Dash = 16
    HDR = 64
    FourK = 128
    DolbyAudio = 256
    DolbyVision = 512
    EighK = 1024
    AV1 = 2048
    HDRVivid = 16384

    def default(self):
        return self.Dash | self.AV1 | self.FourK
