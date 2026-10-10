from __future__ import annotations
import sys, tempfile, unittest, importlib.util, subprocess, os
from pathlib import Path
import h5py
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from extract_features import derive_chunk
from audit_hdf5 import run as run_audit


def toy_tensor():
    # Synthetic test fixture only. Values are invented to exercise code paths.
    a=np.zeros((4,19,4),dtype=np.float32)
    # Event 0: MET + one electron + one muon + two jets.
    a[0,0]=[100,0,0,1]
    a[0,1]=[30,0.2,0.5,2]
    a[0,5]=[40,-1.1,-0.2,3]
    a[0,9]=[80,1.0,1.2,4]
    a[0,10]=[20,-0.3,-1.2,4]
    # Event 1: MET and one jet.
    a[1,0]=[55,0,2.0,1]
    a[1,9]=[45,0.6,2.1,4]
    a[1,3]=[12,0.1,0.2,2.5]  # non-integral type code must be invalid, never rounded to electron
    # Event 2: include one invalid type code and a negative pT on jet.
    a[2,0]=[35,0,-2.2,1]
    a[2,9]=[-2,0.7,0.4,4]
    a[2,2]=[4,0.2,0.1,9]
    # Event 3: deliberate inconsistent zero padding for audit detection.
    a[3,0]=[20,0,0.3,1]
    a[3,18]=[3.0,0.4,0.3,0]
    return a


def make_h5(path:Path):
    with h5py.File(path,'w') as f:
        f.create_dataset('Particles',data=toy_tensor(),chunks=(2,19,4),compression='gzip')
        f.create_dataset('Particles_Names',data=np.asarray([b'pt',b'eta',b'phi']))
        f.create_dataset('Particles_Classes',data=np.asarray([b'padding',b'MET',b'electron',b'muon',b'jet']))


class TestFeatureTransform(unittest.TestCase):
    def test_derives_features_without_dropping_rows(self):
        a=toy_tensor()
        df=derive_chunk(a,0)
        self.assertEqual(len(df),4)
        self.assertEqual(df.iloc[0].event_row_id,0)
        self.assertEqual(df.iloc[0].n_electrons,1)
        self.assertEqual(df.iloc[0].n_muons,1)
        self.assertEqual(df.iloc[0].n_jets,2)
        self.assertAlmostEqual(float(df.iloc[0].ht_jets),100.0,places=4)
        self.assertAlmostEqual(float(df.iloc[0].sum_lepton_pt),70.0,places=4)
        self.assertAlmostEqual(float(df.iloc[0].leading_jet_pt),80.0,places=4)
        self.assertEqual(int(df.iloc[1].invalid_type_count),1)
        self.assertEqual(int(df.iloc[2].invalid_type_count),1)
        self.assertEqual(int(df.iloc[2].negative_pt_count),1)
        self.assertEqual(int(df.iloc[3].inconsistent_padding_count),1)

    def test_chunk_offsets_are_stable(self):
        a=toy_tensor()
        d1=derive_chunk(a[:2],0)
        d2=derive_chunk(a[2:],2)
        self.assertEqual(d1.event_row_id.tolist()+d2.event_row_id.tolist(),[0,1,2,3])


class TestRawAudit(unittest.TestCase):
    def test_full_scan_and_quality_counters(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); source=d/'toy.h5'; make_h5(source)
            report=run_audit(source,d/'audit',chunk_rows=2)
            self.assertEqual(report['status'],'COMPLETED_FULL_FILE_SCAN')
            self.assertEqual(report['scan']['rows_read'],4)
            self.assertEqual(report['scan']['event_rows_skipped'],0)
            self.assertEqual(report['quality']['invalid_type_code_count'],2)
            self.assertEqual(report['quality']['noninteger_type_code_count'],1)
            self.assertEqual(report['quality']['negative_pT_count_occupied_slots'],1)
            self.assertEqual(report['quality']['empty_slots_with_nonzero_kinematics_count'],1)
            self.assertEqual(report['schema']['Particles_shape'],[4,19,4])
            self.assertTrue((d/'audit'/'raw_audit.json').exists())
            self.assertTrue((d/'audit'/'hdf5_inventory.csv').exists())


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "pyarrow installed in Docker image")
class TestParquetETL(unittest.TestCase):
    def test_parquet_etl_preserves_every_fixture_row(self):
        from extract_features import run as run_etl
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); source=d/'toy.h5'; out=d/'events.parquet'; make_h5(source)
            report=run_etl(source,out,chunk_rows=2)
            self.assertEqual(report['input_rows_read'],4)
            self.assertEqual(report['output_rows_written'],4)
            self.assertEqual(report['rows_filtered'],0)
            self.assertEqual(pq.ParquetFile(out).metadata.num_rows,4)


class TestHadoopStreaming(unittest.TestCase):
    def test_mapper_reducer_sum_grouped_rows(self):
        mapper=ROOT/'hadoop/mapper.py'; reducer=ROOT/'hadoop/reducer.py'
        fixture='0\t0\t15\t20\t3\n1\t2\t40\t50\t12\n2\t2\t20\t100\t10\n'
        mapped=subprocess.run([sys.executable,str(mapper)],input=fixture,text=True,capture_output=True,check=True).stdout
        sorted_map='\n'.join(sorted(mapped.strip().splitlines(),key=lambda line:int(line.split('\t',1)[0])))+'\n'
        reduced=subprocess.run([sys.executable,str(reducer)],input=sorted_map,text=True,capture_output=True,check=True).stdout.strip().splitlines()
        self.assertEqual(len(reduced),2)
        group2=[r for r in reduced if r.split('\t')[0]=='2'][0].split('\t')
        self.assertEqual(int(group2[1]),2)
        self.assertAlmostEqual(float(group2[2]),75.0)
        self.assertAlmostEqual(float(group2[3]),30.0)
        self.assertAlmostEqual(float(group2[4]),11.0)

if __name__=='__main__': unittest.main(verbosity=2)
