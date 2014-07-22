"""
Test image featurizer.
"""
from rdkit import Chem

from pande_gas.features import images


def test_images():
    """Test MolImage."""
    mol = Chem.MolFromSmiles(test_smiles)
    f = images.MolImage(250, flatten=True)
    rval = f([mol])
    assert rval.shape == (1, 250 * 250 * 3), rval.shape


def test_images_topo_view():
    """Test MolImage using topo_view."""
    mol = Chem.MolFromSmiles(test_smiles)
    f = images.MolImage(250, flatten=False)
    rval = f([mol])
    assert rval.shape == (1, 250, 250, 3), rval.shape

test_smiles = 'CC(=O)OC1=CC=CC=C1C(=O)O'