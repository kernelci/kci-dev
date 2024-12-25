## How to contribute to kci-dev

#### **Did you find a bug?**

* **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/kernelci/kci-dev/issues).
* If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/kernelci/kci-dev/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

#### **Did you write a patch that fixes a bug?**

* Open a new GitHub pull request with the patch.
* Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.
* Ensure that the PR code pass the GitHub automatic checks, you can use the following suggested [workflow](#make-your-code-pass-automated-code-checks) for be sure everything pass.

#### **Make your code pass automated code checks**

The best way for developing kci-dev is by using [virtualenv](https://virtualenv.pypa.io/en/latest/) and [poetry](https://python-poetry.org/)

```shell
virtualenv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

For executing the automated code checks

```shell
poe check
```

This checks can be automated during git commit  
Just append `poe check` to your pre-commit file
```shell
echo "poe check" >> .git/hooks/pre-commit
```
