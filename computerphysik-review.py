#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright © 2016 Martin Ueding <dev@martin-ueding.de>
# Licensed under The MIT License

import argparse
import os
import shutil
import subprocess
import tempfile

import jinja2


RAW_TEMPLATE = r'''
\documentclass[11pt, ngerman, DIV=18]{scrartcl}

\usepackage{babel}
\usepackage[colorlinks=true, urlcolor=blue]{hyperref}
\usepackage[utf8]{luainputenc}
\usepackage[charter]{mathdesign}
\usepackage{berasans}
\usepackage{beramono}
\usepackage{minted}

\subject{Abgabe in Computerphysik (Sommersemester 2016)}
\title{<< name >> -- Woche << week >>}
\author{%
    Tutor: Martin Ueding \\
    \href{mailto:tutorium@martin-ueding.de}{tutorium@martin-ueding.de}
}

\begin{document}

\maketitle

%< for filename in files >%
\section*{<< filename >>}

\inputminted[
    linenos=true,
    fontfamily=tt,
    fontsize=\small,
    frame=none,
]{c}{<< filename >>}
%< endfor >%

\end{document}
'''

EXTENSIONS = ['.h', '.hpp', '.c', '.cpp']


def order_files(files):
    roots = {}
    for file_ in files:
        root, ext = os.path.splitext(file_)
        if ext not in EXTENSIONS:
            continue

        if root not in roots:
            roots[root] = []

        roots[root].append(ext)

    result = []

    for root, exts in sorted(roots.items()):
        for ext in EXTENSIONS:
            if ext in exts:
                result.append(root + ext)

    return result


def get_name_and_week(path):
    '''
    >>> get_name_and_week('/home/mu/Dokumente/Tutorieren/Computerphysik/Abgaben/Ueding/01')
    ('Ueding', '01')
    '''
    base, week = os.path.split(path)
    ignored, name = os.path.split(base)
    nicename = name.replace('_', ' ').replace('-', ', ')
    return name, nicename, week


def format_c_file(in_path, out_path):
    output = subprocess.check_output(['clang-format', in_path]).decode()
    with open(out_path, 'w') as f:
        f.write(output)


def process_folder(folder, template):
    abs_path = os.path.abspath(folder)

    name, nicename, week = get_name_and_week(abs_path)

    files = os.listdir(folder)
    files = order_files(files)

    with tempfile.TemporaryDirectory() as tempdir:
        for file_ in files:
            formatted_path = os.path.join(tempdir, file_)
            format_c_file(os.path.join(folder, file_), formatted_path)

        rendered = template.render(name=nicename, week=int(week), files=files)

        tex_basename = 'Review-{}-{}.tex'.format(name, week)
        pdf_basename = 'Review-{}-{}.pdf'.format(name, week)
        tex_file = os.path.join(tempdir, tex_basename)
        with open(tex_file, 'w') as f:
            f.write(rendered)

        lualatex_command = ['lualatex', '--enable-write18', '--halt-on-error']
        pdflatex_command = ['pdflatex', '-shell-escape']
        command = pdflatex_command + [tex_basename]
        subprocess.check_call(command, cwd=tempdir)

        print(os.listdir(tempdir))

        shutil.copy(os.path.join(tempdir, pdf_basename),
                    os.path.join(os.path.dirname(abs_path), pdf_basename))


def main():
    options = _parse_args()

    env = jinja2.Environment(
        "%<", ">%",
        "<<", ">>",
        "/*", "*/",
    )
    template = env.from_string(RAW_TEMPLATE)

    for folder in options.folders:
        process_folder(folder, template)


def _parse_args():
    '''
    Parses the command line arguments.

    :return: Namespace with arguments.
    :rtype: Namespace
    '''
    parser = argparse.ArgumentParser(description='Creates big review PDF files for annotations.')
    parser.add_argument('folders', metavar='folder', nargs='+',
                        help='Folders to review')
    options = parser.parse_args()

    return options


if __name__ == '__main__':
    main()
