#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
This script is adapted from the torchvision one.
"""

import os.path

import jinja2
import yaml


# The CUDA versions which have pytorch conda packages available for linux for each
# version of pytorch.
# Pytorch 1.4 also supports cuda 10.0 but we no longer build for cuda 10.0 at all.
CONDA_CUDA_VERSIONS = {
    "1.5.0": ["cu92", "cu101", "cu102"],
    "1.5.1": ["cu92", "cu101", "cu102"],
    "1.6.0": ["cu92", "cu101", "cu102"],
    "1.7.0": ["cu101", "cu102", "cu110"],
    "1.7.1": ["cu101", "cu102", "cu110"],
    "1.8.0": ["cu101", "cu102", "cu111"],
    "1.8.1": ["cu101", "cu102", "cu111"],
    "1.9.0": ["cu102", "cu111"],
}


def pytorch_versions_for_python(python_version):
    if python_version in ["3.6", "3.7", "3.8"]:
        return list(CONDA_CUDA_VERSIONS)
    pytorch_without_py39 = ["1.4", "1.5.0", "1.5.1", "1.6.0", "1.7.0"]
    return [i for i in CONDA_CUDA_VERSIONS if i not in pytorch_without_py39]


def workflows(prefix="", filter_branch=None, upload=False, indentation=6):
    w = []
    for btype in ["conda"]:
        for python_version in ["3.6", "3.7", "3.8", "3.9"]:
            for pytorch_version in pytorch_versions_for_python(python_version):
                for cu_version in CONDA_CUDA_VERSIONS[pytorch_version]:
                    w += workflow_pair(
                        btype=btype,
                        python_version=python_version,
                        pytorch_version=pytorch_version,
                        cu_version=cu_version,
                        prefix=prefix,
                        upload=upload,
                        filter_branch=filter_branch,
                    )

    return indent(indentation, w)


def workflow_pair(
    *,
    btype,
    python_version,
    pytorch_version,
    cu_version,
    prefix="",
    upload=False,
    filter_branch,
):

    w = []
    py = python_version.replace(".", "")
    pyt = pytorch_version.replace(".", "")
    base_workflow_name = f"{prefix}linux_{btype}_py{py}_{cu_version}_pyt{pyt}"

    w.append(
        generate_base_workflow(
            base_workflow_name=base_workflow_name,
            python_version=python_version,
            pytorch_version=pytorch_version,
            cu_version=cu_version,
            btype=btype,
            filter_branch=filter_branch,
        )
    )

    if upload:
        w.append(
            generate_upload_workflow(
                base_workflow_name=base_workflow_name,
                btype=btype,
                cu_version=cu_version,
                filter_branch=filter_branch,
            )
        )

    return w


def generate_base_workflow(
    *,
    base_workflow_name,
    python_version,
    cu_version,
    pytorch_version,
    btype,
    filter_branch=None,
):

    d = {
        "name": base_workflow_name,
        "python_version": python_version,
        "cu_version": cu_version,
        "pytorch_version": pytorch_version,
        "context": "DOCKERHUB_TOKEN",
    }

    if filter_branch is not None:
        d["filters"] = {"branches": {"only": filter_branch}}

    return {f"binary_linux_{btype}": d}


def generate_upload_workflow(*, base_workflow_name, btype, cu_version, filter_branch):
    d = {
        "name": f"{base_workflow_name}_upload",
        "context": "org-member",
        "requires": [base_workflow_name],
    }

    if btype == "wheel":
        d["subfolder"] = cu_version + "/"

    if filter_branch is not None:
        d["filters"] = {"branches": {"only": filter_branch}}

    return {f"binary_{btype}_upload": d}


def indent(indentation, data_list):
    if len(data_list) == 0:
        return ""
    return ("\n" + " " * indentation).join(
        yaml.dump(data_list, default_flow_style=False).splitlines()
    )


if __name__ == "__main__":
    d = os.path.dirname(__file__)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(d),
        lstrip_blocks=True,
        autoescape=False,
        keep_trailing_newline=True,
    )

    with open(os.path.join(d, "config.yml"), "w") as f:
        f.write(env.get_template("config.in.yml").render(workflows=workflows))
