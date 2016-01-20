# Written by Evan N. Feinberg at Stanford University, contact: enf@stanford.edu
from copy import deepcopy
import numpy as np
import time
from collections import deque
import hashlib
import sys
import openbabel as ob
from functools import partial


'''
http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
'''


def merge_two_dicts(x, y):
  '''Given two dicts, merge them into a new dict as a shallow copy.'''
  z = x.copy()
  z.update(y)
  return z

def compute_centroid(coordinates):
  '''given molecule, an instance of class PDB, compute the x,y,z centroid of that molecule'''

  centroid = np.mean(coordinates, axis=0)
  return(centroid)


def generate_random_unit_vector():
  '''generate a random unit vector on the 3-sphere
  citation:
  http://mathworld.wolfram.com/SpherePointPicking.html

  a. Choose random theta \element [0, 2*pi]
  b. Choose random z \element [-1, 1]
  c. Compute output: (x,y,z) = (sqrt(1-z^2)*cos(theta), sqrt(1-z^2)*sin(theta),z)
  d. output u
  '''

  theta = np.random.uniform(low=0.0, high=2 * np.pi)
  z = np.random.uniform(low=-1.0, high=1.0)
  u = np.array([np.sqrt(1 - z**2) * np.cos(theta),
          np.sqrt(1 - z**2) * np.sin(theta), z])
  return(u)


def generate_random_rotation_matrix():
  '''
   1. generate a random unit vector, i.e., randomly sampled from the unit 3-sphere
    a. see function generate_random_unit_vector() for details
    2. Generate a second random unit vector thru the algorithm in (1), output v
    a. If absolute value of u \dot v > 0.99, repeat. This is important for numerical stability
      (intuition: we want them to be as linearly independent as possible or else the
      orthogonalized version of v will be much shorter in magnitude compared to u. I assume
      in Stack they took this from Gram-Schmidt orthogonalization?)
    b. v' = v - (u \dot v)*u, i.e. subtract out the component of v that's in u's direction
    c. normalize v' (this isn't in Stack but I assume it must be done)
    3. find w = u \cross v'
    4. u, v', and w will form the columns of a rotation matrix, R. The intuition is that
      u, v' and w are, respectively, what the standard basis vectors e1, e2, and e3 will be
      mapped to under the transformation.
  '''

  u = generate_random_unit_vector()
  v = generate_random_unit_vector()
  while np.abs(np.dot(u, v)) >= 0.99:
    v = generate_random_unit_vector()

  vp = v - (np.dot(u, v) * u)
  vp /= np.linalg.norm(vp)

  w = np.cross(u, vp)

  R = np.column_stack((u, vp, w))
  return(R)


def rotate_molecules(mol_coordinates_list):
  '''
  Pseudocode:
  1. Generate random rotation matrix. This matrix applies a random transformation to any
    3-vector such that, were the random transformation repeatedly applied, it would randomly
    sample along the surface of a sphere with radius equal to the norm of the given 3-vector
    cf. generate_random_rotation_matrix() for details
  2. Apply R to all atomic coordinatse.
  3. Return rotated molecule
  '''
  R = generate_random_rotation_matrix()
  rotated_coordinates_list = []

  for mol_coordinates in mol_coordinates_list:
    coordinates = deepcopy(mol_coordinates)
    rotated_coordinates = np.transpose(
      np.dot(R, np.transpose(coordinates)))
    rotated_coordinates_list.append(rotated_coordinates)

  return(rotated_coordinates_list)


def reflect_molecule(mol_coordinates_list):
  '''
  Pseudocode:
  1. Generate unit vector that is randomly distributed around 3-sphere
  2. For each atom, project its coordinates onto the random unit vector from (1),
    and subtract twice the projection from the original coordinates to obtain its reflection
  '''

  molecule = deepcopy(mol)
  a = generate_random_unit_vector()
  reflected_coordinates_list = []

  for mol_coordinates in mol_coordinates_list:
    coordinates = deepcopy(mol_coordinates)
    reflected_coordinates = coordinates - 2. * \
      (np.dot(v, a) / (np.dot(a, a)) * a)
    reflected_coordinates_list.append(reflected_coordinates)
  return(reflected_coordinates_list)


def compute_pairwise_distances(protein_xyz, ligand_xyz):
  '''
  Takes an input m x 3 and n x 3 np arrays of 3d coords of protein and ligand,
  respectively, and outputs an m x n np array of pairwise distances in Angstroms
  between protein and ligand atoms. entry (i,j) is dist between the i'th protein
  atom and the j'th ligand atom
  '''

  pairwise_distances = np.zeros(
    (np.shape(protein_xyz)[0], np.shape(ligand_xyz)[0]))
  for j in range(0, np.shape(ligand_xyz)[0]):
    differences = protein_xyz - ligand_xyz[j, :]
    squared_differences = np.square(differences)
    pairwise_distances[:, j] = np.sqrt(np.sum(squared_differences, 1))

  return(pairwise_distances)

'''following two functions adapted from:
http://stackoverflow.com/questions/2827393/angles-between-two-n-dimensional-vectors-in-python
'''


def unit_vector(vector):
  """ Returns the unit vector of the vector.  """
  return vector / np.linalg.norm(vector)


def angle_between(vector_i, vector_j):
  """ Returns the angle in radians between vectors 'vector_i' and 'vector_j'::

      >>> angle_between((1, 0, 0), (0, 1, 0))
      1.5707963267948966
      >>> angle_between((1, 0, 0), (1, 0, 0))
      0.0
      >>> angle_between((1, 0, 0), (-1, 0, 0))
      3.141592653589793
  """
  vector_i_u = unit_vector(vector_i)
  vector_j_u = unit_vector(vector_j)
  angle = np.arccos(np.dot(vector_i_u, vector_j_u))
  if np.isnan(angle):
    if (vector_i_u == vector_j_u).all():
      return 0.0
    else:
      return np.pi
  return angle


def bfs(mol, startatom, D):
  '''
  given openbabel molecule and a starting atom of type OBAtom,
  finds all bonds out to degree D via a breath-first search
  '''

  visited_atoms = set()
  atoms_to_add = []
  bonds_to_add = []
  queue = deque([(startatom, 0)])
  while queue:
    atom, depth = queue.popleft()
    index = atom.GetIndex()
    visited_atoms.add(index)
    atomtype = atom.GetType()
    if depth < D:
      for bond in ob.OBAtomBondIter(atom):
        if bond not in bonds_to_add:
          bonds_to_add.append(bond)
    if depth < D:
      for atom in ob.OBAtomAtomIter(atom):
        if atom.GetIndex() not in visited_atoms:
          queue.append((atom, depth + 1))
  return(bonds_to_add)


def construct_fragment_from_bonds(bonds):
  '''
  takes as input a list of bonds of type OBBond and constructs a new
  openbabel molecule from those bonds and the atoms that constitute
  the start and end of those bonds.
  '''

  fragment = ob.OBMol()
  added_atoms = []

  for bond in bonds:
    atom_i = bond.GetBeginAtom()
    atom_j = bond.GetEndAtom()

    if atom_i not in added_atoms:
      fragment.AddAtom(atom_i)
      added_atoms.append(atom_i)
    atom_i_index = added_atoms.index(atom_i)

    if atom_j not in added_atoms:
      fragment.AddAtom(atom_j)
      added_atoms.append(atom_j)
    atom_j_index = added_atoms.index(atom_j)

    fragment.AddBond(
      atom_i_index + 1,
      atom_j_index + 1,
      bond.GetBondOrder())

  for i, fragment_bond in enumerate(ob.OBMolBondIter(fragment)):
    mol_bond = bonds[i]
    if mol_bond.IsAromatic():
      fragment_bond.SetAromatic()

  return(fragment)


def compute_ecfp(system_ob, start_atom, max_degree=2):
  '''
  Given an openbabel molecule and a starting atom (OBAtom object),
  compute the ECFP[max_degree]-like representation for that atom.
  Returns (for now) a SMILES string representing the resulting fragment.

  TODO(enf): Optimize this! Try InChi key and other approaches
  to improving this representation.
  '''

  fragment = ob.OBMol()

  bonds_to_add = bfs(system_ob, start_atom, max_degree)
  fragment = construct_fragment_from_bonds(bonds_to_add)
  obConversion = ob.OBConversion()
  obConversion.SetOutFormat("can")
  smiles = obConversion.WriteString(fragment).split("\t")[0]
  return(smiles)

def hash_sybyl(sybyl, sybyl_types):
  return(sybyl_types.index(sybyl))

def hash_ecfp(ecfp, power):
  '''
  Returns an int of size 2^power representing that
  ECFP fragment. Input must be a string.
  '''

  md5 = hashlib.md5()
  md5.update(ecfp)
  digest = md5.hexdigest()
  ecfp_hash = int(digest, 16) % (2 ** power)
  return(ecfp_hash)


def hash_ecfp_pair(ecfp_pair, power):
  '''
  Returns an int of size 2^power representing that
  ECFP pair. Input must be a tuple of strings.
  '''

  ecfp = "%s,%s" % (ecfp_pair[0], ecfp_pair[1])
  md5 = hashlib.md5()
  md5.update(ecfp)
  digest = md5.hexdigest()
  ecfp_hash = int(digest, 16) % (2 ** power)
  return(ecfp_hash)


def compute_all_ecfp(system_ob, indices=None, degree=2):
  '''
  For each atom:
    Obtain molecular fragment for all atoms emanating outward to given degree.
    For each fragment, compute SMILES string (for now) and hash to an int.
    Return a dictionary mapping atom index to hashed SMILES.
  '''

  ecfp_dict = {}

  for atom in ob.OBMolAtomIter(system_ob):
    if indices is not None and atom.GetIndex() not in indices:
      continue
    ecfp_dict[atom.GetIndex()] = "%s,%s" % (
      atom.GetType(), compute_ecfp(system_ob, atom, degree))

  return(ecfp_dict)


def compute_ecfp_features(system_ob, ecfp_degree, ecfp_power):
  '''
  Takes as input an openbabel molecule, ECFP radius, and number of bits to store
  ECFP features (2^ecfp_power will be length of ECFP array);
  Returns an array of size 2^ecfp_power where array at index i has a 1 if that ECFP fragment
  is found in the molecule and array at index j has a 0 if ECFP fragment not in molecule.
  '''

  ecfp_dict = compute_all_ecfp(system_ob, degree=ecfp_degree)
  ecfp_vec = [hash_ecfp(ecfp, ecfp_power)
        for index, ecfp in ecfp_dict.iteritems()]
  ecfp_array = np.zeros(2 ** ecfp_power)
  ecfp_array[sorted(ecfp_vec)] = 1.0
  return(ecfp_array)


def featurize_binding_pocket_ecfp(protein_xyz, protein, ligand_xyz, ligand,
                  pairwise_distances=None, cutoff=4.5, ecfp_degree=2):
  '''
  Computes ECFP dicts for both the ligand and the binding pocket region of the protein.
  '''

  features_dict = {}

  if pairwise_distances is None:
    pairwise_distances = compute_pairwise_distances(
      protein_xyz, ligand_xyz)
  contacts = np.nonzero((pairwise_distances < 4.5))
  protein_atoms = set([int(c) for c in contacts[0].tolist()])

  protein_ecfp_dict = compute_all_ecfp(
    protein, indices=protein_atoms, degree=ecfp_degree)
  ligand_ecfp_dict = compute_all_ecfp(ligand, degree=ecfp_degree)

  return (protein_ecfp_dict, ligand_ecfp_dict)

def compute_all_sybyl(system_ob, indices=None):
  sybyl_dict = {}

  for atom in ob.OBMolAtomIter(system_ob):
    if indices is not None and atom.GetIndex() not in indices:
      continue
    sybyl_dict[atom.GetIndex()] = atom.GetType()

  return(sybyl_dict)


def featurize_binding_pocket_sybyl(protein_xyz, protein, ligand_xyz, ligand,
                                   pairwise_distances=None, cutoff=7.0):
  features_dict = {}

  if pairwise_distances is None:
    pairwise_distances = compute_pairwise_distances(
      protein_xyz, ligand_xyz)
  contacts = np.nonzero((pairwise_distances < cutoff))
  protein_atoms = set([int(c) for c in contacts[0].tolist()])

  protein_sybyl_dict = compute_all_sybyl(protein, indices=protein_atoms)
  ligand_sybyl_dict = compute_all_sybyl(ligand)
  return (protein_sybyl_dict, ligand_sybyl_dict)

def compute_splif_features_in_range(protein, ligand, pairwise_distances, contact_bin,
                  ecfp_degree=2):
  '''
  Find all protein atoms that are > contact_bin[0] and < contact_bin[1] away from ligand atoms.
  Then, finds the ECFP fingerprints for the contacting atoms.
  Returns a dictionary mapping (protein_index_i, ligand_index_j) --> (protein_ecfp_i, ligand_ecfp_j)
  '''
  contacts = np.nonzero(
    (pairwise_distances > contact_bin[0]) & (
      pairwise_distances < contact_bin[1]))
  protein_atoms = set([int(c) for c in contacts[0].tolist()])
  contacts = zip(contacts[0], contacts[1])

  protein_ecfp_dict = compute_all_ecfp(
    protein, indices=protein_atoms, degree=ecfp_degree)
  ligand_ecfp_dict = compute_all_ecfp(ligand, degree=ecfp_degree)
  splif_dict = {
    contact: (
      protein_ecfp_dict[
        contact[0]], ligand_ecfp_dict[
        contact[1]]) for contact in contacts}
  return(splif_dict)


def featurize_splif(protein_xyz, protein, ligand_xyz, ligand, contact_bins, pairwise_distances,
          ecfp_degree):
  '''
  For each contact range (i.e. 1 A to 2 A, 2 A to 3 A, etc.) compute a dictionary mapping
  (protein_index_i, ligand_index_j) tuples --> (protein_ecfp_i, ligand_ecfp_j) tuples.
  return a list of such splif dictionaries.
  '''

  if pairwise_distances is None:
    pairwise_distances = compute_pairwise_distances(
      protein_xyz, ligand_xyz)
  splif_dicts = []
  for i, contact_bin in enumerate(contact_bins):
    splif_dicts.append(
      compute_splif_features_in_range(
        protein,
        ligand,
        pairwise_distances,
        contact_bin,
        ecfp_degree))

  return(splif_dicts)

def compute_ring_center(mol, ring):
  ring_xyz = np.zeros((len(ring._path), 3))
  for i, atom_idx in enumerate(ring._path):
    atom = mol.GetAtom(atom_idx)
    ring_xyz[i, :] = [atom.x(), atom.y(), atom.z()]
  ring_centroid = compute_centroid(ring_xyz)
  return ring_centroid

def compute_ring_normal(mol, ring):
  points = np.zeros((3,3))
  for i, atom_idx in enumerate(ring._path):
    if i == 3: break
    atom = mol.GetAtom(atom_idx)
    points[i,:] = [atom.x(), atom.y(), atom.z()]

  v1 = points[1,:] - points[0,:]
  v2 = points[2,:] - points[0,:]
  normal = np.cross(v1, v2)
  return normal

def is_pi_parallel(protein_ring_center, protein_ring_normal, 
                  ligand_ring_center, ligand_ring_normal):
  dist = np.linalg.norm(protein_ring_center-ligand_ring_center)
  angle = angle_between(protein_ring_normal, ligand_ring_normal) * 180 / np.pi
  if ((np.abs(angle) < 30.0) 
       or (np.abs(angle) > 150.0 and np.abs(angle) < 210.0)
       or (np.abs(angle) > 330.0 and np.abs(angle) < 360.0)):
    if dist < 8.0:
      return True

  return False

def is_pi_t(protein_ring_center, protein_ring_normal, 
            ligand_ring_center, ligand_ring_normal):
  dist = np.linalg.norm(protein_ring_center-ligand_ring_center)
  angle = angle_between(protein_ring_normal, ligand_ring_normal) * 180 / np.pi
  if ((np.abs(angle) > 60.0 and np.abs(angle) < 120.0) 
       or (np.abs(angle) > 240.0 and np.abs(angle) < 300.0)):
    if dist < 5.5:
      return True

  return False

def update_feature_dict(feature_dict, idxs=None, indices=None):
  if idxs is not None:
    indices = []
    for idx in idxs:
      indices.append(idx-1)

  for index in indices:
    if index not in feature_dict.keys():
      feature_dict[index] = 1
    else:
      feature_dict[index] += 1 

  return feature_dict 

def compute_pi_stack(protein_xyz, protein, ligand_xyz, ligand,
                    pairwise_distances=None, dist_cutoff=4.4, 
                    angle_cutoff=30.):
  '''
  Pseudocode: 

  for each ring in ligand:
    if it is aromatic: 
      for each ring in protein:
        if it is aromatic:
          compute distance between centers
          compute angle. 
          if it counts as parallel pi-pi: 
            for each atom in ligand and in protein, 
              add to list of atom indices 
          if it counts as pi-T:
            for each atom in ligand and in protein:
              add to list of atom indices
  '''
  protein_pi_parallel = {}
  protein_pi_t = {}
  ligand_pi_parallel = {}
  ligand_pi_t = {}

  for protein_ring in ob.OBMolRingIter(protein):
    if protein_ring.IsAromatic():
      protein_ring_center = compute_ring_center(protein, protein_ring)
      protein_ring_normal = compute_ring_normal(protein, protein_ring)
      
      ligand_pi_parallel_idxs = set()
      ligand_pi_t_idxs = set()
      for ligand_ring in ob.OBMolRingIter(ligand):
        if len(ligand_pi_parallel_idxs) > 0:
          print ligand_pi_parallel_idxs
        if ligand_ring.IsAromatic():


          ligand_ring_center = compute_ring_center(ligand, ligand_ring)
          ligand_ring_normal = compute_ring_normal(ligand, ligand_ring)

          if is_pi_parallel(protein_ring_center, protein_ring_normal, 
                            ligand_ring_center, ligand_ring_normal):
            protein_pi_parallel = update_feature_dict(protein_pi_parallel,
                                                      idxs=protein_ring._path)

            ligand_idxs_to_update = list(set(ligand_ring._path)-ligand_pi_parallel_idxs)
            ligand_pi_parallel = update_feature_dict(ligand_pi_parallel,
                                                     idxs=ligand_idxs_to_update)
            ligand_pi_parallel_idxs.update(set(ligand_ring._path))
          
          if is_pi_t(protein_ring_center, protein_ring_normal, 
                            ligand_ring_center, ligand_ring_normal):
            protein_pi_t = update_feature_dict(protein_pi_t,
                                               idxs=protein_ring._path)

            ligand_idxs_to_update = list(set(ligand_ring._path)-ligand_pi_t_idxs)
            ligand_pi_t = update_feature_dict(ligand_pi_t,
                                              idxs=ligand_idxs_to_update)
            ligand_pi_t_idxs.update(set(ligand_ring._path))

  return (protein_pi_t, protein_pi_parallel, ligand_pi_t, ligand_pi_parallel)

def is_cation_pi(cation_position, ring_center, ring_normal):
  cation_to_ring_vec = cation_position - ring_center
  dist = np.linalg.norm(cation_to_ring_vec)
  angle = angle_between(cation_to_ring_vec, ring_normal) * 180. / np.pi 
  if dist < 6.5:
    if ((np.abs(angle) < 30.0) or
        (np.abs(angle) > 150.0 and np.abs(angle) < 210.0) or
        (np.abs(angle) > 330.0 and np.abs(angle) < 360.0)):
      return True 

  return False

def compute_cation_pi(protein, ligand, protein_cation_pi, ligand_cation_pi):
  for protein_ring in ob.OBMolRingIter(protein):
    if protein_ring.IsAromatic():
      protein_ring_center = compute_ring_center(protein, protein_ring)
      protein_ring_normal = compute_ring_normal(protein, protein_ring)
      for atom in ob.OBMolAtomIter(ligand):
        if np.abs(atom.GetFormalCharge() - 1.0) < 0.01 or '+' in atom.GetType():
          cation_position = np.array([atom.x(), atom.y(), atom.z()])
          if is_cation_pi(cation_position, protein_ring_center, protein_ring_normal):
            protein_cation_pi = update_feature_dict(protein_cation_pi, 
                                                    idxs=protein_ring._path)
            ligand_cation_pi = update_feature_dict(ligand_cation_pi,
                                                    indices=[atom.GetIndex()])
  return protein_cation_pi, ligand_cation_pi

def compute_binding_pocket_cation_pi(protein_xyz, protein, ligand_xyz, ligand):
  protein_cation_pi = {}
  ligand_cation_pi = {}

  (protein_cation_pi, ligand_cation_pi) = compute_cation_pi(protein, ligand, protein_cation_pi,
                                                          ligand_cation_pi)
  (ligand_cation_pi, protein_cation_pi) = compute_cation_pi(ligand, protein, ligand_cation_pi,
                                                          protein_cation_pi)
  return (protein_cation_pi, ligand_cation_pi)

def get_formal_charge(atom):
  if '+' in atom.GetType() or np.abs(1.0-atom.GetFormalCharge()) < 0.01:
    return 1
  elif '-' in atom.GetType() or np.abs(-1.0-atom.GetFormalCharge()) < 0.01:
    return -1
  else:
    return atom.GetFormalCharge()

def is_salt_bridge(atom_i, atom_j):
  if np.abs(2.0-np.abs(get_formal_charge(atom_i)-get_formal_charge(atom_j))) < 0.01:
     return True
  else:
    return False

def compute_salt_bridges(protein_xyz, protein, ligand_xyz, ligand, pairwise_distances):
  salt_bridge_contacts = []

  contacts = np.nonzero(pairwise_distances < 5.0)
  contacts = zip(contacts[0], contacts[1])
  for contact in contacts:
    protein_atom = protein.GetAtom(contact[0]+1)
    ligand_atom = ligand.GetAtom(contact[1]+1)
    if is_salt_bridge(protein_atom, ligand_atom):
      salt_bridge_contacts.append(contact)
  return salt_bridge_contacts

def is_angle_within_cutoff(vector_i, vector_j, hbond_angle_cutoff):
  angle = angle_between(vector_i, vector_j) * 180. / np.pi
  return(angle > (180 - hbond_angle_cutoff) and angle < (180. + hbond_angle_cutoff))


def is_hydrogen_bond(protein_xyz, protein, ligand_xyz,
           ligand, contact, hbond_angle_cutoff):
  '''
  Determine if a pair of atoms (contact = tuple of protein_atom_index, ligand_atom_index)
  between protein and ligand represents a hydrogen bond. Returns a boolean result.
  '''

  protein_atom_index = contact[0]
  ligand_atom_index = contact[1]
  protein_atom = protein.GetAtom(protein_atom_index+1)
  ligand_atom = ligand.GetAtom(ligand_atom_index+1)
  if protein_atom.IsHbondAcceptor() and ligand_atom.IsHbondDonor():
    for atom in ob.OBAtomAtomIter(ligand_atom):
      if atom.GetAtomicNum() == 1:
        hydrogen_xyz = ligand_xyz[atom.GetIndex(), :]
        vector_i = protein_xyz[protein_atom_index, :] - hydrogen_xyz
        vector_j = ligand_xyz[ligand_atom_index, :] - hydrogen_xyz
        return is_angle_within_cutoff(
          vector_i, vector_j, hbond_angle_cutoff)

  elif ligand_atom.IsHbondAcceptor() and protein_atom.IsHbondDonor():
    for atom in ob.OBAtomAtomIter(protein_atom):
      if atom.GetAtomicNum() == 1:
        hydrogen_xyz = protein_xyz[atom.GetIndex(), :]
        vector_i = protein_xyz[protein_atom_index, :] - hydrogen_xyz
        vector_j = ligand_xyz[ligand_atom_index, :] - hydrogen_xyz
        return is_angle_within_cutoff(
          vector_i, vector_j, hbond_angle_cutoff)

  return False


def compute_hbonds_in_range(protein, protein_xyz, ligand, ligand_xyz,
                            pairwise_distances, hbond_dist_bin, 
                            hbond_angle_cutoff, ecfp_degree):
  '''
  Find all pairs of (protein_index_i, ligand_index_j) that hydrogen bond given
  a distance bin and an angle cutoff.
  '''

  contacts = np.nonzero(
    (pairwise_distances > hbond_dist_bin[0]) & (
      pairwise_distances < hbond_dist_bin[1]))
  protein_atoms = set([int(c) for c in contacts[0].tolist()])
  protein_ecfp_dict = compute_all_ecfp(
    protein, indices=protein_atoms, degree=ecfp_degree)
  ligand_ecfp_dict = compute_all_ecfp(ligand, degree=ecfp_degree)
  contacts = zip(contacts[0], contacts[1])
  hydrogen_bond_contacts = []
  for contact in contacts:
    if is_hydrogen_bond(protein_xyz, protein, ligand_xyz,
              ligand, contact, hbond_angle_cutoff):
      hydrogen_bond_contacts.append(contact)
  return hydrogen_bond_contacts


def compute_hydrogen_bonds(protein_xyz, protein, ligand_xyz, ligand, 
                           pairwise_distances, hbond_dist_bins, 
                           hbond_angle_cutoffs, ecfp_degree):
  '''
  Returns a list of sublists. Each sublist is a series of tuples of (protein_index_i, ligand_index_j)
  that represent a hydrogen bond. Each sublist represents a different type of hydrogen bond.
  '''

  hbond_contacts = []
  for i, hbond_dist_bin in enumerate(hbond_dist_bins):
    hbond_angle_cutoff = hbond_angle_cutoffs[i]
    hbond_contacts.append(compute_hbonds_in_range(protein, protein_xyz, ligand, 
                                                  ligand_xyz, pairwise_distances, 
                                                  hbond_dist_bin, hbond_angle_cutoff, 
                                                  ecfp_degree))
  return(hbond_contacts)


def convert_atom_to_voxel(molecule_xyz, atom_index, box_width, voxel_width):
  '''
  Converts an atom to an i,j,k grid index.
  '''
  coordinates = molecule_xyz[atom_index, :]
  indices = np.floor(np.abs(molecule_xyz[atom_index, :] +
                            np.array([box_width, box_width, box_width]) / 2.0) 
                            / voxel_width).astype(int)
  return([indices])


def convert_atom_pair_to_voxel(
    molecule_xyz_tuple, atom_index_pair, box_width, voxel_width):
  '''
  Converts a pair of atoms to a list of i,j,k tuples.
  '''
  indices_list = []
  indices_list.append(convert_atom_to_voxel(molecule_xyz_tuple[0],
                        atom_index_pair[0], box_width, voxel_width)[0])
  indices_list.append(convert_atom_to_voxel(molecule_xyz_tuple[1],
                        atom_index_pair[1], box_width, voxel_width)[0])
  return(indices_list)

def merge_molecules(self, protein_xyz, protein, ligand_xyz, ligand):
  '''
  Takes as input protein and ligand objects of class PDB and adds ligand atoms to the protein,
  and returns the new instance of class PDB called system that contains both sets of atoms.
  '''

  system_xyz = np.array(np.vstack(np.vstack((protein_xyz, ligand_xyz))))
  system_ob = ob.OBMol(protein_ob)
  system_ob += ligand_ob

  return system_xyz, system_ob

def subtract_centroid(xyz, centroid):
  '''
  subtracts the centroid, a numpy array of dim 3, from all coordinates of all atoms in the molecule
  '''

  xyz -= np.transpose(centroid)
  return(xyz)

class grid_featurizer:

  def __init__(self, box_x=16.0, box_y=16.0, box_z=16.0,
         nb_rotations=0, nb_reflections=0, feature_types="ecfp",
         ecfp_degree=2, ecfp_power=3, splif_power=3,
         save_intermediates=False, ligand_only=False,
         box_width=16.0, voxel_width=1.0, voxelize_features=True, 
         voxel_feature_types=[], **kwargs):

    self.box_x = float(box_x) / 10.0
    self.box_y = float(box_y) / 10.0
    self.box_z = float(box_z) / 10.0

    self.ecfp_degree = ecfp_degree
    self.ecfp_power = ecfp_power
    self.splif_power = splif_power

    self.nb_rotations = nb_rotations
    self.nb_reflections = nb_reflections
    self.feature_types = feature_types

    self.save_intermediates = save_intermediates
    self.ligand_only = ligand_only

    self.hbond_dist_bins = [(2.2, 2.5), (2.5, 3.2), (3.2, 4.0)]
    self.hbond_angle_cutoffs = [5, 50, 90]
    self.contact_bins = [(0, 2.0), (2.0, 3.0), (3.0, 4.5)]

    self.box_width = float(box_width)
    self.voxel_width = float(voxel_width)
    self.voxels_per_edge = self.box_width / self.voxel_width
    self.voxelize_features = voxelize_features
    self.voxel_feature_types = voxel_feature_types

    self.sybyl_types = ["C3", "C2", "C1", "Cac", "Car", "N3", "N3+", "Npl", "N2", "N1", "Ng+",
                        "Nox", "Nar", "Ntr", "Nam", "Npl3", "N4", "O3", "O-", "O2", "O.co2",
                        "O.spc", "O.t3p", "S3", "S3+", "S2", "So2", "Sox" "Sac" "SO", "P3", 
                        "P", "P3+", "F", "Cl", "Br", "I"]

  def transform(self, protein_pdb, ligand_pdb, save_dir):
    '''Takes as input files (strings) for pdb of the protein, pdb of the ligand, and a directory
    to save intermediate files.

    This function then computes the centroid of the ligand; decrements this centroid from the atomic coordinates of protein and
    ligand atoms, and then merges the translated protein and ligand. This combined system/complex is then saved.

    This function then computes a featurization with scheme specified by the user.
    '''
    a = time.time()
    protein_name = str(protein_pdb).split(
      "/")[len(str(protein_pdb).split("/")) - 2]

    if not self.ligand_only:
      protein_xyz, protein_ob = self.load_molecule(protein_pdb, calc_charges=True)
    ligand_xyz, ligand_ob = self.load_molecule(ligand_pdb, calc_charges=True)



    if "ecfp" in self.feature_types:
      ecfp_array = compute_ecfp_features(
        ligand_ob, self.ecfp_degree, self.ecfp_power)
      return({(0, 0): ecfp_array})

    centroid = compute_centroid(ligand_xyz)
    ligand_xyz = subtract_centroid(ligand_xyz, centroid)
    if not self.ligand_only:
      protein_xyz = subtract_centroid(protein_xyz, centroid)

    if "splif" in self.feature_types:
      splif_array = self.featurize_splif(
        protein_xyz, protein_ob, ligand_xyz, ligand_ob)
      return({(0, 0): splif_array})

    if "flat_combined" in self.feature_types:
      return(self.compute_flat_features(protein_xyz, protein_ob, 
                                        ligand_xyz, ligand_ob))

    pairwise_distances = compute_pairwise_distances(protein_xyz, ligand_xyz)
    if "ecfp" in self.voxel_feature_types:
      protein_ecfp_dict, ligand_ecfp_dict = featurize_binding_pocket_ecfp(protein_xyz, protein_ob, ligand_xyz,
                                          ligand_ob, pairwise_distances, cutoff=4.5, ecfp_degree=self.ecfp_degree)
    if "splif" in self.voxel_feature_types: 
      splif_dicts = featurize_splif(protein_xyz, protein_ob, ligand_xyz, ligand_ob, self.contact_bins, pairwise_distances,
                  self.ecfp_degree)

    if "hbond" in self.voxel_feature_types:
      hbond_list = compute_hydrogen_bonds(protein_xyz, protein_ob, ligand_xyz, ligand_ob, pairwise_distances,
                      self.hbond_dist_bins, self.hbond_angle_cutoffs, self.ecfp_degree)          

    if "sybyl" in self.voxel_feature_types:
      protein_sybyl_dict, ligand_sybyl_dict = featurize_binding_pocket_sybyl(protein_xyz, protein_ob, ligand_xyz,
                                                                           ligand_ob, pairwise_distances, cutoff=7.0)

    if "pi_stack" in self.voxel_feature_types:
      protein_pi_t, protein_pi_parallel, ligand_pi_t, ligand_pi_parallel = compute_pi_stack(protein_xyz, protein_ob,
                                                                                            ligand_xyz, ligand_ob, 
                                                                                            pairwise_distances)

    if "cation_pi" in self.voxel_feature_types:
      protein_cation_pi, ligand_cation_pi = compute_binding_pocket_cation_pi(protein_xyz, protein_ob, ligand_xyz, ligand_ob)

    if "salt_bridge" in self.voxel_feature_types:
      salt_bridge_list = compute_salt_bridges(protein_xyz, protein_ob, ligand_xyz, ligand_ob, pairwise_distances)

    transformed_systems = {}
    transformed_systems[(0, 0)] = [protein_xyz, ligand_xyz]

    for i in range(0, int(self.nb_rotations)):
      rotated_system = rotate_molecules([protein_xyz, ligand_xyz])
      transformed_systems[(i + 1, 0)] = rotated_system
      for j in range(0, int(self.nb_reflections)):
        reflected_system = self.reflect_molecule(rotated_system)
        transformed_systems[(i + 1, j + 1)] = reflected_system

    if "voxel_combined" in self.feature_types:
      features = {}
      for system_id, system in transformed_systems.iteritems():
        protein_xyz = system[0]
        ligand_xyz = system[1]
        feature_tensors = []
        if "ecfp" in self.voxel_feature_types:
          ecfp_tensor = self.voxelize(convert_atom_to_voxel, hash_ecfp, protein_xyz,
                           feature_dict=protein_ecfp_dict, channel_power=self.ecfp_power)
          ecfp_tensor += self.voxelize(convert_atom_to_voxel, hash_ecfp, ligand_xyz,
                           feature_dict=ligand_ecfp_dict, channel_power=self.ecfp_power)
          feature_tensors.append(ecfp_tensor)
          print("Completed ecfp tensor")
        
        if "splif" in self.voxel_feature_types: 

          feature_tensors += [self.voxelize(convert_atom_pair_to_voxel, hash_ecfp_pair, (protein_xyz, ligand_xyz),
                            feature_dict=splif_dict, channel_power=self.splif_power) for splif_dict in splif_dicts]
          print("Completed splif tensor")

        if "hbond" in self.voxel_feature_types:

          feature_tensors += [self.voxelize(convert_atom_pair_to_voxel, None, (protein_xyz, ligand_xyz),
                              feature_list=hbond, channel_power=0) for hbond in hbond_list]
          print("Completed hbond tensor")

        if "sybyl" in self.voxel_feature_types:

          sybyl_partial = partial(hash_sybyl, sybyl_types=self.sybyl_types)
          sybyl_tensor = self.voxelize(convert_atom_to_voxel, hash_sybyl, protein_xyz, feature_dict=protein_sybyl_dict, 
                                               nb_channel=len(self.sybyl_types))
          sybyl_tensor += self.voxelize(convert_atom_to_voxel, hash_sybyl, ligand_xyz, feature_dict=ligand_sybyl_dict, 
                                               nb_channel=len(self.sybyl_types))
          feature_tensors.append(sybyl_tensor)  
          print("Completed sybyl tensor")        

        if "pi_stack" in self.voxel_feature_types:
          pi_parallel_tensor = self.voxelize(convert_atom_to_voxel, None, protein_xyz,
                                               feature_dict=protein_pi_parallel, nb_channel=1)
          pi_parallel_tensor += self.voxelize(convert_atom_to_voxel, None, ligand_xyz,
                                               feature_dict=ligand_pi_parallel, nb_channel=1)
          feature_tensors.append(pi_parallel_tensor)

          pi_t_tensor = self.voxelize(convert_atom_to_voxel, None, protein_xyz,
                                               feature_dict=protein_pi_t, nb_channel=1)
          pi_t_tensor += self.voxelize(convert_atom_to_voxel, None, ligand_xyz,
                                               feature_dict=ligand_pi_t, nb_channel=1)
          feature_tensors.append(pi_t_tensor)
          print("Completed pi_stack tensor")

        if "cation_pi" in self.voxel_feature_types:
          cation_pi_tensor = self.voxelize(convert_atom_to_voxel, None, protein_xyz,
                                           feature_dict=protein_cation_pi, nb_channel=1)
          cation_pi_tensor += self.voxelize(convert_atom_to_voxel, None, ligand_xyz,
                                            feature_dict=ligand_cation_pi, nb_channel=1)
          feature_tensors.append(cation_pi_tensor)
          print("Completed cation_pi tensor.")

        if "salt_bridge" in self.voxel_feature_types:
          if len(salt_bridge_list) > 0:
            salt_bridge_tensor = self.voxelize(convert_atom_pair_to_voxel, None, (protein_xyz, ligand_xyz),
                                            feature_list=salt_bridge_list, nb_channel=1)
            feature_tensors.append(salt_bridge_tensor)

          print("Completed salt_bridge tensor.")

        feature_tensor = np.concatenate(feature_tensors, axis=3)
        features[system_id] = feature_tensor

      return(features)

  def voxelize(self, get_voxels, hash_function, coordinates,
         feature_dict=None, feature_list=None, 
         channel_power=None, nb_channel=16):
  #TODO(enf): make array index checking not a try-catch statement.
    if channel_power is not None:
      if channel_power == 0:
        nb_channel = 1
      else:
        nb_channel = int(2**channel_power)
    feature_tensor = np.zeros(
      (self.voxels_per_edge,
       self.voxels_per_edge,
       self.voxels_per_edge,
       nb_channel),
      dtype=np.int8)
    if feature_dict is not None:
      for key, features in feature_dict.iteritems():
        voxels = get_voxels(
          coordinates, key, self.box_width, self.voxel_width)
        for voxel in voxels:  
          try:
            if hash_function is not None:
              feature_tensor[
                voxel[0], voxel[1], voxel[2], hash_function(
                  features, channel_power)] += 1.0
            else:
              feature_tensor[
                voxel[0], voxel[1], voxel[3], 0] += features
          except:
            continue
    elif feature_list is not None:
      for key in feature_list:
        voxels = get_voxels(
          coordinates, key, self.box_width, self.voxel_width)
        for voxel in voxels:
          try:
            feature_tensor[voxel[0], voxel[1], voxel[2], 0] += 1.0
          except:
            continue

    return feature_tensor

  def vectorize(self, hash_function, feature_dict=None,
          feature_list=None, channel_power=10):
    feature_vector = np.zeros(2**channel_power)
    if feature_dict is not None:
      on_channels = [
        hash_function(
          feature,
          channel_power) for key,
        feature in feature_dict.iteritems()]
      feature_vector[on_channels] += 1
    elif feature_list is not None:
      feature_vector[0] += len(feature_list)

    return feature_vector

  def get_xyz_from_ob(self, ob_mol):
    '''
    returns an m x 3 np array of 3d coords
    of given openbabel molecule
    '''

    xyz = np.zeros((ob_mol.NumAtoms(), 3))
    for i, atom in enumerate(ob.OBMolAtomIter(ob_mol)):
      xyz[i, 0] = atom.x()
      xyz[i, 1] = atom.y()
      xyz[i, 2] = atom.z()
    return(xyz)

  def load_molecule(self, molecule_file, remove_hydrogens=True, calc_charges=False):
    '''
    given molecule_file, returns a tuple of xyz coords of molecule
    and an openbabel object representing that molecule
    '''

    if ".mol2" in molecule_file:
      obConversion = ob.OBConversion()
      obConversion.SetInAndOutFormats("mol2", "mol2")
      ob_mol = ob.OBMol()
      obConversion.ReadFile(ob_mol, molecule_file)

    else:
      obConversion = ob.OBConversion()
      obConversion.SetInAndOutFormats("pdb", "pdb")
      ob_mol = ob.OBMol()
      obConversion.ReadFile(ob_mol, molecule_file)

    if calc_charges:
      gasteiger = ob.OBChargeModel.FindType("gasteiger")
      gasteiger.ComputeCharges(ob_mol)
      ob_mol.UnsetImplicitValencePerceived()
      ob_mol.CorrectForPH(7.4)
      ob_mol.AddHydrogens()
    else:
      ob_mol.AddHydrogens()

    xyz = self.get_xyz_from_ob(ob_mol)

    return xyz, ob_mol

  def generate_box(self, mol):
    '''
    generate_box takes as input a molecule of class PDB and removes all atoms outside of the given box dims
    '''

    molecule = deepcopy(mol)
    atoms_to_keep = []
    all_atoms = [a for a in molecule.topology.atoms]
    for atom in all_atoms:
      coords = np.abs(molecule.xyz[0][atom.index, :])
      if coords[0] <= (self.box_x / 2.) and coords[1] <= (self.box_y /
                                2.) and coords[2] <= (self.box_z / 2.):
        atoms_to_keep.append(atom.index)
    return(molecule.atom_slice(atoms_to_keep))

  def compute_flat_features(self, protein_xyz, protein_ob, ligand_xyz, ligand_ob):
      pairwise_distances = compute_pairwise_distances(
        protein_xyz, ligand_xyz)
      protein_ecfp_dict, ligand_ecfp_dict = featurize_binding_pocket_ecfp(protein_xyz, protein_ob, ligand_xyz,
                                        ligand_ob, pairwise_distances, cutoff=4.5, ecfp_degree=self.ecfp_degree)
      splif_dicts = featurize_splif(protein_xyz, protein_ob, ligand_xyz, ligand_ob, self.contact_bins, pairwise_distances,
                      self.ecfp_degree)
      hbond_list = compute_hydrogen_bonds(protein_xyz, protein_ob, ligand_xyz, ligand_ob, pairwise_distances,
                        self.hbond_dist_bins, self.hbond_angle_cutoffs, self.ecfp_degree)

      protein_ecfp_vector = [
        self.vectorize(
          hash_ecfp,
          feature_dict=protein_ecfp_dict,
          channel_power=self.ecfp_power)]
      ligand_ecfp_vector = [
        self.vectorize(
          hash_ecfp,
          feature_dict=ligand_ecfp_dict,
          channel_power=self.ecfp_power)]
      splif_vectors = [
        self.vectorize(
          hash_ecfp_pair,
          feature_dict=splif_dict,
          channel_power=self.splif_power) for splif_dict in splif_dicts]
      hbond_vectors = [self.vectorize(hash_ecfp_pair, feature_list=hbond_list, channel_power=0)
               for hbond_class in hbond_list]
      feature_vectors = protein_ecfp_vector + \
        ligand_ecfp_vector + splif_vectors + hbond_vectors
      feature_vector = np.concatenate(feature_vectors, axis=0)

      return({(0, 0): feature_vector})
