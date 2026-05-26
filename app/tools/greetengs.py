from app.utils.shuffle_bag import ShuffleBag

GREETENGS_SHUFFLE = None

def get_greetengs():
    global GREETENGS_SHUFFLE
    if GREETENGS_SHUFFLE is None:
        GREETENGS_SHUFFLE = ShuffleBag(list([
            "Привет!",
            "Привет-привет!",
            "Н+ИХ+АО!",
            "Прив+етики! А теперь звезд+уй раб+отать.",
            "Плодотв+орных сверш+ений!"
        ]))
    return GREETENGS_SHUFFLE.pick()