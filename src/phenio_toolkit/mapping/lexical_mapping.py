import os
import re
from typing import List

import curies
import pandas as pd

UPHENO_PREFIX = "http://purl.obolibrary.org/obo/UPHENO_"
OBO_PREFIX = "http://purl.obolibrary.org/obo/"


def _invert_dol_nonunique(d):
    newdict = {}
    for k in d:
        for v in d[k]:
            newdict.setdefault(v, []).append(k)
    return newdict


def _merge_label_equivalent_cliques(dd_rv):
    merge_labels = dict()
    for iri in dd_rv:
        labels_to_merge = dd_rv.get(iri)
        if len(labels_to_merge) > 1:
            for lab in labels_to_merge:
                if lab not in merge_labels:
                    merge_labels[lab] = []
                merge_labels[lab] = list(set(merge_labels[lab] + labels_to_merge))
    return merge_labels


def _pairwise(t):
    it = iter(t)
    return zip(it, it)


class LexicalMapping:
    def __init__(
        self,
        upheno_species_lexical,
        upheno_mapping_logical,
        stopwords: List[str],
    ):
        self.upheno_species_lexical = upheno_species_lexical
        self.upheno_mapping_logical = upheno_mapping_logical
        self.stopwords = stopwords

    def _apply_stopword(self, value):
        for stopword in self.stopwords:
            if value and stopword in value:
                return "abnormal " + value.replace(stopword, "")
            return value

    def _load_upheno_mappings(self):
        df = pd.read_csv(self.upheno_species_lexical)
        df.columns = ["iri", "p", "label"]
        dfl1 = pd.read_csv(self.upheno_mapping_logical)[["p1", "p2"]]
        dfl2 = dfl1.copy()
        dfl2.columns = ["p2", "p1"]
        dfl = pd.concat([dfl1, dfl2], ignore_index=True, sort=False)
        ## Load logical mappings
        dfl = dfl.drop_duplicates()
        dfl["cat"] = "logical"

        ## Prepare dataframe for labels
        df_label = df[df["p"] == "http://www.w3.org/2000/01/rdf-schema#label"][["iri", "label"]]
        df_label.columns = ["iri", "label"]
        return df, df_label, dfl

    def _preprocess_labels(self, df):
        df["label"] = df["label"].astype(str)
        df["label_pp"] = df["label"].apply(lambda x: re.sub(r"[(][A-Z]+[)]", "", x))
        df["label_pp"] = df["label_pp"].str.lower()
        df["label_pp"] = df["label_pp"].apply(lambda x: re.sub(r"[^0-9a-z' ]", "", x))

        df["label_pp"] = df["label_pp"].apply(lambda x: self._apply_stopword(x))

        df["label_pp"] = df["label_pp"].str.strip()
        df.dropna(subset=["label_pp"], inplace=True)
        df["label_pp"] = df["label_pp"].apply(lambda x: re.sub(r"[\s]+", " ", x))
        df = df[~df["iri"].astype(str).str.startswith(UPHENO_PREFIX)]
        df = df[df["label_pp"] != ""]
        d = df[["iri", "label_pp"]]
        d.columns = ["iri", "label"]
        d = d.drop_duplicates()
        return d

    def _compute_mappings(self, dd, l):
        dd_rv = _invert_dol_nonunique(dd)
        merge_labels = _merge_label_equivalent_cliques(dd_rv)

        data = []
        done = set()
        for label in dd:
            if label in done:
                continue
            done.add(label)
            iris = dd.get(label)
            if label in merge_labels:
                for lab in merge_labels[label]:
                    iris.extend(dd.get(lab))
                    done.add(lab)
            iris = list(set(iris))
            if len(iris) > 1:
                pairs = _pairwise(iris)
                for pair in pairs:
                    data.append([pair[0], pair[1]])
                    data.append([pair[1], pair[0]])
        df_mappings = pd.DataFrame.from_records(data)
        df_mappings = df_mappings.drop_duplicates()
        df_mappings["cat"] = "lexical"
        df_mappings.columns = ["p1", "p2", "cat"]
        df_maps = pd.merge(df_mappings, l, how="left", left_on=["p1"], right_on=["iri"])
        df_maps = pd.merge(df_maps, l, how="left", left_on=["p2"], right_on=["iri"])
        df_maps["o1"] = [
            re.sub("_\d+", "", iri.replace(OBO_PREFIX, "")) for iri in df_maps["p1"].values
        ]
        df_maps["o2"] = [
            re.sub("_\d+", "", iri.replace(OBO_PREFIX, "")) for iri in df_maps["p2"].values
        ]
        return df_maps

    def generate_mapping_files(self, output):
        "generate_mapping_files."
        df, df_label, dfl = self._load_upheno_mappings()
        l = df_label[~df_label["iri"].astype(str).str.startswith(UPHENO_PREFIX)]
        # track match field, then add to the final table
        d = self._preprocess_labels(df)
        dd = d.groupby("label")["iri"].apply(list).to_dict()
        file_names = [
            "upheno_custom_mapping.sssom.tsv",
            "mapping_lexical.csv",
            "upheno_lexical_mapping.robot.template.tsv",
            "mapping_problematic.csv",
        ]
        (
            mapping_all,
            mapping_lexical,
            mapping_lexical_template,
            mapping_problematic,
        ) = [os.path.join(output, file_name) for file_name in file_names]

        df_mapping = self._compute_mappings(dd, l)

        w = df_mapping[df_mapping["o1"] == df_mapping["o2"]]
        df_maps = df_mapping[df_mapping["o1"] != df_mapping["o2"]]
        w.to_csv(mapping_problematic, index=False)

        df_mapping_template = df_mapping[["p1", "p2"]].copy()
        df_mapping_template.columns = ["Ontology ID", "EquivalentClasses"]

        new_row = pd.DataFrame(
            [["ID", "AI obo:UPHENO_0000002"]], columns=["Ontology ID", "EquivalentClasses"]
        )
        df_mapping_template = pd.concat([new_row, df_mapping_template]).reset_index(drop=True)

        df_mapping.to_csv(mapping_lexical, index=False)
        df_mapping_template.to_csv(mapping_lexical_template, index=False, sep="\t")

        df_m = pd.merge(df_maps[["p1", "p2", "cat"]], dfl, how="outer", on=["p1", "p2"])
        df_m = pd.merge(df_m, l, how="left", left_on=["p1"], right_on=["iri"])
        df_m = df_m.drop("iri", axis=1)
        df_m = pd.merge(df_m, l, how="left", left_on=["p2"], right_on=["iri"])
        df_m["cat"] = df_m["cat_x"].astype(str) + "-" + df_m["cat_y"].astype(str)

        df_m = df_m.drop(["iri", "cat_x", "cat_y"], axis=1)
        df_m["cat"] = df_m["cat"].str.replace(r"(^nan-)|(-nan$)", "", regex=True)

        obo_converter = curies.get_obo_converter()
        custom_converter = curies.Converter(
            [
                curies.Record(
                    prefix="MGPO",
                    prefix_synonyms=[],
                    uri_prefix="http://purl.obolibrary.org/obo/MGPO_",
                    uri_prefix_synonyms=[],
                )
            ]
        )
        converter = curies.chain([obo_converter, custom_converter])

        df_m["subject_id"] = df_m.apply(
            lambda x: converter.compress_or_standardize(x["p1"]), axis=1
        )

        df_m["object_id"] = df_m.apply(lambda x: converter.compress_or_standardize(x["p2"]), axis=1)

        df_m["subject_source"] = df_m.apply(
            lambda x: f"obo:{str(x['subject_id']).split(':', maxsplit=1)[0].lower()}", axis=1
        )

        df_m["object_source"] = df_m.apply(
            lambda x: f"obo:{str(x['object_id']).split(':', maxsplit=1)[0].lower()}", axis=1
        )

        #
        df_m["mapping_justification"] = df_m["cat"].map(
            {
                "lexical": "semapv:LexicalMatching",
                "logical": "semapv:LogicalMatching",
                "lexical-logical": "semapv:LexicalAndLogicalMatching",
            }
        )

        df_m["predicate_id"] = "semapv:crossSpeciesExactMatch"
        df_m["subject_category"] = "biolink:PhenotypicFeature"
        df_m["object_category"] = "biolink:PhenotypicFeature"

        df_m = df_m.rename(
            columns={
                # "p1": "subject_id",
                "label_x": "subject_label",
                # "p2": "object_id",
                "label_y": "object_label",
            }
        )[
            [
                "subject_id",
                "subject_label",
                "subject_source",
                "predicate_id",
                "object_id",
                "object_label",
                "object_source",
                "mapping_justification",
            ]
        ]
        df_m.to_csv(mapping_all, sep="\t", index=False)
