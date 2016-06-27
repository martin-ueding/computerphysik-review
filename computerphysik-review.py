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
\documentclass[11pt, ngerman, DIV=18, parskip=full]{scrartcl}

\usepackage{babel}
\usepackage[colorlinks=true, urlcolor=blue]{hyperref}
\usepackage[utf8x]{luainputenc}
\usepackage[charter]{mathdesign}
\usepackage{berasans}
\usepackage{beramono}
\usepackage{minted}
\usepackage{multicol}
\usepackage{booktabs}

\subject{Abgabe in Computerphysik (Sommersemester 2016)}
\title{Woche << week >>}
\author{%
    << name >>
}
\publishers{%
    Tutor: Martin Ueding
    (\href{mailto:tutorium@martin-ueding.de}{tutorium@martin-ueding.de})
}

\begin{document}

\maketitle

\begin{center}
    \begin{tabular}{llr}
        \toprule
        Teil & erreicht & möglich \\
        \midrule
        Aufgaben && 18 \\
        Stil && 2 \\
        \midrule
        Summe && 20 \\
        \bottomrule
    \end{tabular}

    \vspace{2ex}

    \begin{minipage}{.5\textwidth}
        Dies ist der Quelltext, den du abgegeben hast. Ich habe ihn mit meinem
        Standard-Stil umformatiert, damit ich es bei der Korrektur etwas einfacher
        habe. Der Inhalt vom Code hat sich aber nicht geändert.
    \end{minipage}
\end{center}

%< for basename, filename, language in files >%
\section*{<< basename >>}

\inputminted[
    linenos=true,
    fontfamily=tt,
    fontsize=\small,
    frame=none,
]{<< language >>}{<< filename >>}
\clearpage
%< endfor >%

\section*{Zusätzliche Kommentare}

\end{document}
'''

EXT_C = ['.h', '.hpp', '.c', '.cpp']
EXT_IMG = ['.pdf']
EXT_TXT = ['.txt', '.dat']
EXT_DIFF = ['.diff', '.patch']


def decode(s, encodings=('utf8', 'latin1', 'ascii')):
    ''' http://stackoverflow.com/a/273631 '''
    for encoding in encodings:
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass
        return s.decode('ascii', 'ignore')


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
    >>> get_name_and_week('/home/mu/Dokumente/Tutorieren/Computerphysik/Abgaben/01/Ueding')
    ('01', 'Ueding')
    '''
    base, name = os.path.split(path)
    ignored, week = os.path.split(base)
    nicename = name.replace('_', ' ').replace('--', r' \and ')
    return name, nicename, week


def format_c_file(in_path, out_path):
    output = decode(subprocess.check_output(['clang-format', in_path]))
    print(output)
    with open(out_path, 'w') as f:
        f.write(output)


def format_txt_file(in_path, out_path):
    with open(in_path) as f:
        output = subprocess.check_output(['par'], stdin=f).decode()
    with open(out_path, 'w') as f:
        f.write(output)


def process_folder(folder, files, template):
    abs_path = os.path.abspath(folder)

    name, nicename, week = get_name_and_week(abs_path)

    #files = order_files(files)

    is_c = lambda x: os.path.splitext(x.lower())[1] in EXT_C
    is_txt = lambda x: os.path.splitext(x.lower())[1] in EXT_TXT
    is_diff = lambda x: os.path.splitext(x.lower())[1] in EXT_DIFF
    is_pdf = lambda x: os.path.splitext(x.lower())[1] == '.pdf'
    is_make = lambda x: x.lower() == 'makefile'

    pdf_files = list(filter(is_pdf, files))

    with tempfile.TemporaryDirectory() as tempdir:
        for_minted = []
        for file_ in files:
            basename = os.path.basename(file_)
            tex_name = file_.replace('_', r'\_')
            temp_dirname = os.path.join(tempdir, os.path.dirname(file_))
            subprocess.call(['ls', '-la', tempdir])
            subprocess.check_call(['mkdir', '-p', temp_dirname])
            temp_path = os.path.join(tempdir, file_)
            if is_c(basename):
                formatted_path = os.path.join(tempdir, file_)
                format_c_file(os.path.join(folder, file_), formatted_path)
                for_minted.append((tex_name, formatted_path, 'c'))
            elif is_txt(basename):
                #formatted_path = os.path.join(tempdir, file_)
                #format_txt_file(os.path.join(folder, file_), formatted_path)
                #for_minted.append((basename, formatted_path, 'text'))
                shutil.copy(file_, temp_path)
                for_minted.append((tex_name, temp_path, 'text'))
            elif is_make(basename):
                shutil.copy(file_, temp_path)
                for_minted.append((tex_name, temp_path, 'make'))
            elif is_diff(basename):
                shutil.copy(file_, temp_path)
                for_minted.append((tex_name, temp_path, 'diff'))

        print(for_minted)

        assert len(for_minted) > 0, "No files selected for rendering"

        rendered = template.render(name=nicename, week=int(week), files=for_minted)

        tex_basename = 'Review-{}-{}.tex'.format(name, week)
        pdf_basename = 'Review-{}-{}.pdf'.format(name, week)
        tex_file = os.path.join(tempdir, tex_basename)
        with open(tex_file, 'w') as f:
            f.write(rendered)

        lualatex_command = ['lualatex', '--enable-write18', '--halt-on-error']
        pdflatex_command = ['latexrun', '--latex-args', '-shell-escape -halt-on-error']
        command = pdflatex_command + [tex_basename]
        try:
            subprocess.check_call(command, cwd=tempdir)
        except subprocess.CalledProcessError as e:
            print(e)
            with open(os.path.join(tempdir, tex_basename)) as f:
                print(f.read())
            raise

        print(os.listdir(tempdir))

        command = ['pdfunite', os.path.join(tempdir, pdf_basename)] \
                + pdf_files \
                + [pdf_basename]
        print(command)
        subprocess.check_call(command)


def main():
    options = _parse_args()

    env = jinja2.Environment(
        "%<", ">%",
        "<<", ">>",
        "/*", "*/",
    )
    template = env.from_string(RAW_TEMPLATE)

    process_folder(os.getcwd(), options.files, template)


def _parse_args():
    '''
    Parses the command line arguments.

    :return: Namespace with arguments.
    :rtype: Namespace
    '''
    parser = argparse.ArgumentParser(description='Creates big review PDF files for annotations.')
    parser.add_argument('files', nargs='+', help='Files to review')
    options = parser.parse_args()

    return options


if __name__ == '__main__':
    main()
