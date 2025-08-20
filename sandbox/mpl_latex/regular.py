import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris

matplotlib.use('pgf')
plt.rcParams.update({
  "text.usetex": True,
  "pgf.texsystem": "xelatex",
  "pgf.rcfonts": False,
  "pgf.preamble": r"\usepackage{fontspec}\setsansfont{Neue Haas Grotesk Display Pro}"
})
FILENAME = "iris-xelatex.png"

iris = load_iris()
iris_df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
iris_df['species'] = iris.target
iris_df['species_name'] = iris.target_names[iris.target]

plt.figure(dpi=300)
fig, ax = plt.subplots()
setosa = iris_df[iris_df['species_name'] == 'setosa']
versicolor = iris_df[iris_df['species_name'] == 'versicolor']
virginica = iris_df[iris_df['species_name'] == 'virginica']
ax.scatter(setosa['sepal length (cm)'], setosa['sepal width (cm)'], label='setosa')
ax.scatter(versicolor['sepal length (cm)'], versicolor['sepal width (cm)'], label='versicolor')
ax.scatter(virginica['sepal length (cm)'], virginica['sepal width (cm)'], label='virginica')
plt.grid(axis='y', alpha=0.3)

plt.title('Distribution of Petal Length', fontsize=28)
plt.xlabel('Petal Length $L$ [cm]', fontsize=26)
plt.ylabel('Frequency $f$', fontsize=26)
ax.legend(fontsize=20)

plt.savefig(FILENAME, dpi=300, bbox_inches='tight')
