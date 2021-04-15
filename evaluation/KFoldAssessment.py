import os
import pickle as pkl, numpy as np
from sklearn.model_selection import KFold

from HoldOutSelection import HoldOutSelector
from experiment import Experiment

class KFoldAssessment:
    def __init__(self, num_folds, exp_path, parameter_ranges, num_configs=100):
        self.num_folds = num_folds
        self.kf = KFold(num_folds)
        self.model_selector = HoldOutSelector(num_configs=num_configs)
        self.parameter_ranges = parameter_ranges
        self.exp_path = exp_path
        self._BASE_FOLDER = os.path.join(exp_path, str(self.num_folds) + '_CV')
        self._FOLD_BASE = 'FOLD_'
        self._RESULTS_FILENAME = 'winner_results.pkl'
        self._CONFIG_FILENAME = 'winner_config.pkl'
        self._ASSESSMENT_FILENAME = 'assessment_results.pkl'
        
    def process_results(self):
        TR_hits1 = []
        TS_hits1 = []
        TR_hits10 = []
        TS_hits10 = []
        assessment_results = {}

        for k in range(self.num_folds):
            try:
                results_filename = os.path.join(self._BASE_FOLDER, self._FOLD_BASE + str(k+1),
                                               self._RESULTS_FILENAME)

                with open(results_filename, 'rb') as fp:
                    fold_scores = pkl.load(fp)

                    TR_hits1.append(fold_scores['TR_hits1'])
                    TS_hits1.append(fold_scores['TS_hits1'])
                    TR_hits10.append(fold_scores['TR_hits10'])
                    TS_hits10.append(fold_scores['TS_hits10'])

            except Exception as e:
                print(e)

        TR_hits1 = np.array(TR_hits1)
        TS_hits1 = np.array(TS_hits1)
        TR_hits10 = np.array(TR_hits10)
        TS_hits10 = np.array(TS_hits10)

        assessment_results['avg_TR_hits1'] = TR_hits1.mean()
        assessment_results['std_TR_hits1'] = TR_hits1.std()
        assessment_results['avg_TS_hits1'] = TS_hits1.mean()
        assessment_results['std_TS_hits1'] = TS_hits1.std()
        assessment_results['avg_TR_hits10'] = TR_hits10.mean()
        assessment_results['std_TR_hits10'] = TR_hits10.std()
        assessment_results['avg_TS_hits10'] = TS_hits10.mean()
        assessment_results['std_TS_hits10'] = TS_hits10.std()

        with open(os.path.join(self._BASE_FOLDER, self._ASSESSMENT_FILENAME), 'wb') as fp:
            pkl.dump(assessment_results, fp)
        print(f'Assessment for experiment {self._BASE_FOLDER} has ended\nResults:\n{assessment_results}')
        
        return assessment_results
        
    def risk_assessment(self, dataset, device):
        
        if not os.path.exists(self._BASE_FOLDER):
            os.makedirs(self._BASE_FOLDER)
        
        for k, (tr_idx, ts_idx) in enumerate(self.kf.split(dataset.y.T)):
            fold_dir = os.path.join(self._BASE_FOLDER, self._FOLD_BASE+str(k+1))
            if not os.path.exists(fold_dir):
                os.makedirs(fold_dir)
            
            resultspkl = os.path.join(fold_dir, self._RESULTS_FILENAME)
            if os.path.exists(resultspkl):
                print(f'{resultspkl} already exists! Proceeding to the next fold')
                continue
            else:
                dataset.to(device)
                self._risk_assessment_helper(dataset, tr_idx, ts_idx, fold_dir, device)
                
        assessment_results = self.process_results()
        
        return assessment_results
        
    def _risk_assessment_helper(self, dataset, tr_idx, ts_idx, fold_dir, device):
        winner_config = self.model_selector.model_selection(dataset, tr_idx, self.parameter_ranges, fold_dir, device)
        exp = Experiment() #some path
        tr_hits1, ts_hits1, tr_hits10, ts_hits10 = [], [], [], []
        
        for i in range(3):
            tr_h1, ts_h1, tr_h10, ts_h10 = exp.run_valid(dataset, tr_idx, ts_idx, winner_config, device)
            tr_hits1.append(tr_h1)
            ts_hits1.append(ts_h1)
            tr_hits10.append(tr_h10)
            ts_hits10.append(ts_h10)
            
        tr_hits1 = sum(tr_hits1) / 3
        ts_hits1 = sum(ts_hits1) / 3
        tr_hits10 = sum(tr_hits10) / 3
        ts_hits10 = sum(ts_hits10) / 3
        
        print(f'END OF FOLD.\nTR:\t@1: {tr_hits1:.03f} @10: {tr_hits10:.03f} \
        TS:\t@1: {ts_hits1:.03f} @10: {ts_hits10:.03f}')
        
        results_dict = {'TR_hits1': tr_hits1, 'TS_hits1': ts_hits1,
                        'TR_hits10': tr_hits10, 'TS_hits10': ts_hits10}
        
        with open(os.path.join(fold_dir, self._RESULTS_FILENAME), 'wb') as fp:
            pkl.dump(results_dict, fp)
        with open(os.path.join(fold_dir, self._CONFIG_FILENAME), 'wb') as fp:
            pkl.dump(winner_config, fp)
    