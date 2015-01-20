import pandas as pd


def get_scores(filename, modify=True):
    """
    Get scores and dataset divisions.
    """
    df = pd.read_table(filename)
    scores = {}
    ref_idx = 1
    new_idx = 27
    datasets = {'PCBA': [], 'MUV': [], 'TOX': [], 'DUDE': []}
    print df.values[ref_idx][0], 'VS.', df.values[new_idx][0]  # print scores
    for name, ref_score, new_score in zip(
            df.columns[1:], df.values[ref_idx][1:], df.values[new_idx][1:]):
        score = new_score - ref_score
        original = name
        dataset = None
        if name.startswith('PCBA'):
            name = name.split('PCBA-AID')[-1]
            dataset = 'PCBA'
        elif name.startswith('MUV'):
            name = name.split('MUV-')[-1]
            dataset = 'MUV'
        elif name.startswith('TOX'):
            name = name.split('-')
            name.pop()
            name.pop(0)
            name = '_'.join(name)
            dataset = 'TOX'
        elif name.startswith('DUDE'):
            name = name.split('DUDE-')[-1]
            dataset = 'DUDE'
        else:
            raise ValueError(name)
        if not modify:
            name = original.lower()
        scores[name] = score
        datasets[dataset].append(name)

    # sanity checks
    total = 0
    for key in datasets:
        total += len(datasets[key])
    assert total == 259, total

    return scores, datasets