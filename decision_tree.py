"""Implementation of the CART algorithm to train decision tree classifiers."""
# https://towardsdatascience.com/decision-tree-from-scratch-in-python-46e99dfea775

import numpy as np
import tree


class DecisionTreeClassifier:
    def __init__(self, max_depth=None):
        self.max_depth = max_depth

    def fit(self, X, y):
        """Build decision tree classifier."""
        self.n_classes_ = len(set(y))  # classes are assumed to go from 0 to n-1
        self.n_features_ = X.shape[1]
        self.tree_ = self._grow_tree(X, y)

    def predict(self, X):
        """Predict class for X."""
        return [self._predict(inputs) for inputs in X]

    def debug(self, feature_names, class_names, show_details=True):
        """Print ASCII visualization of decision tree."""
        self.tree_.debug(feature_names, class_names, show_details)

    def _gini(self, y):
        """Compute Gini impurity of a non-empty node.
        Gini impurity is defined as Σ p(1-p) over all classes, with p the frequency of a
        class within the node. Since Σ p = 1, this is equivalent to 1 - Σ p^2.
        """
        m = y.size
        return 1.0 - sum((np.sum(y == c) / m) ** 2 for c in range(self.n_classes_))

    def _best_split(self, X, y):
        """Find the best split for a node.
        "Best" means that the average impurity of the two children, weighted by their
        population, is the smallest possible. Additionally it must be less than the
        impurity of the current node.
        To find the best split, we loop through all the features, and consider all the
        midpoints between adjacent training samples as possible thresholds. We compute
        the Gini impurity of the split generated by that particular feature/threshold
        pair, and return the pair with smallest impurity.
        Returns:
            best_idx: Index of the feature for best split, or None if no split is found.
            best_thr: Threshold to use for the split, or None if no split is found.
        """
        # Need at least two elements to split a node.
        m = y.size
        if m <= 1:
            return None, None

        # Count of each class in the current node.
        num_parent = [np.sum(y == c) for c in range(self.n_classes_)]

        # Gini of current node.
        best_gini = 1.0 - sum((n / m) ** 2 for n in num_parent)
        best_idx, best_thr = None, None

        # Loop through all features.
        for idx in range(self.n_features_):
            # Sort data along selected feature.
            thresholds, classes = zip(*sorted(zip(X[:, idx], y)))

            # We could actually split the node according to each feature/threshold pair
            # and count the resulting population for each class in the children, but
            # instead we compute them in an iterative fashion, making this for loop
            # linear rather than quadratic.
            num_left = [0] * self.n_classes_
            num_right = num_parent.copy()
            for i in range(1, m):  # possible split positions
                c = classes[i - 1]
                num_left[c] += 1
                num_right[c] -= 1
                gini_left = 1.0 - sum(
                    (num_left[x] / i) ** 2 for x in range(self.n_classes_)
                )
                gini_right = 1.0 - sum(
                    (num_right[x] / (m - i)) ** 2 for x in range(self.n_classes_)
                )

                # The Gini impurity of a split is the weighted average of the Gini
                # impurity of the children.
                gini = (i * gini_left + (m - i) * gini_right) / m

                # The following condition is to make sure we don't try to split two
                # points with identical values for that feature, as it is impossible
                # (both have to end up on the same side of a split).
                if thresholds[i] == thresholds[i - 1]:
                    continue

                if gini < best_gini:
                    best_gini = gini
                    best_idx = idx
                    best_thr = (thresholds[i] + thresholds[i - 1]) / 2  # midpoint

        return best_idx, best_thr

    def _grow_tree(self, X, y, depth=0):
        """Build a decision tree by recursively finding the best split."""
        # Population for each class in current node. The predicted class is the one with
        # largest population.
        num_samples_per_class = [np.sum(y == i) for i in range(self.n_classes_)]
        predicted_class = np.argmax(num_samples_per_class)
        node = tree.Node(
            gini=self._gini(y),
            num_samples=y.size,
            num_samples_per_class=num_samples_per_class,
            predicted_class=predicted_class,
        )

        # Split recursively until maximum depth is reached.
        if depth < self.max_depth:
            idx, thr = self._best_split(X, y)
            if idx is not None:
                indices_left = X[:, idx] < thr
                X_left, y_left = X[indices_left], y[indices_left]
                X_right, y_right = X[~indices_left], y[~indices_left]
                node.feature_index = idx
                node.threshold = thr
                node.left = self._grow_tree(X_left, y_left, depth + 1)
                node.right = self._grow_tree(X_right, y_right, depth + 1)
        return node

    def _predict(self, inputs):
        """Predict class for a single sample."""
        node = self.tree_
        while node.left:
            if inputs[node.feature_index] < node.threshold:
                node = node.left
            else:
                node = node.right
        return node.predicted_class


if __name__ == "__main__":
    import argparse
    import pandas as pd
    from sklearn.datasets import load_breast_cancer, load_iris
    from sklearn.tree import DecisionTreeClassifier as SklearnDecisionTreeClassifier
    from sklearn.tree import export_graphviz
    from sklearn.utils import Bunch

    parser = argparse.ArgumentParser(description="Train a decision tree.")
    parser.add_argument("--dataset", choices=["breast", "iris", "wifi"], default="wifi")
    parser.add_argument("--max_depth", type=int, default=1)
    parser.add_argument("--hide_details", dest="hide_details", action="store_true")
    parser.set_defaults(hide_details=False)
    parser.add_argument("--use_sklearn", dest="use_sklearn", action="store_true")
    parser.set_defaults(use_sklearn=False)
    args = parser.parse_args()

    # 1. Load dataset.
    if args.dataset == "breast":
        dataset = load_breast_cancer()
    elif args.dataset == "iris":
        dataset = load_iris()
    elif args.dataset == "wifi":
        # https://archive.ics.uci.edu/ml/datasets/Wireless+Indoor+Localization
        df = pd.read_csv("wifi_localization.txt", delimiter="\t")
        data = df.to_numpy()
        dataset = Bunch(
            data=data[:, :-1],
            target=data[:, -1] - 1,
            feature_names=["Wifi {}".format(i) for i in range(1, 8)],
            target_names=["Room {}".format(i) for i in range(1, 5)],
        )
    X, y = dataset.data, dataset.target

    # 2. Fit decision tree.
    if args.use_sklearn:
        clf = SklearnDecisionTreeClassifier(max_depth=args.max_depth)
    else:
        clf = DecisionTreeClassifier(max_depth=args.max_depth)
    clf.fit(X, y)

    # 3. Predict.
    if args.dataset == "iris":
        input = [0, 0, 5.0, 1.5]
    elif args.dataset == "wifi":
        input = [-70, 0, 0, 0, -40, 0, 0]
    elif args.dataset == "breast":
        input = [np.random.rand() for _ in range(30)]
    pred = clf.predict([input])[0]
    print("Input: {}".format(input))
    print("Prediction: " + dataset.target_names[pred])

    # 4. Visualize.
    if args.use_sklearn:
        export_graphviz(
            clf,
            out_file="tree.dot",
            feature_names=dataset.feature_names,
            class_names=dataset.target_names,
            rounded=True,
            filled=True,
        )
        print("Done. To convert to PNG, run: dot -Tpng tree.dot -o tree.png")
    else:
        clf.debug(
            list(dataset.feature_names),
            list(dataset.target_names),
            not args.hide_details,
        )