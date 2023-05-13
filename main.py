from praatio import textgrid
from os.path import join
from os import walk


class Sentence:
    def __init__(self, transcription, translation):
        self.transcription = transcription
        self.translation = translation


class ReferenceTrackingDevice:
    def __init__(self, form, referent, device, start, end, source_sentence):
        self.form = form
        self.referent = referent
        self.device = device
        self.start = start
        self.end = end
        self.source_sentence = source_sentence


class GridText:
    def __init__(self, filename, translation, cyrillic_transcription, latin_transcription,
                 annotation_form, annotation_indexation, annotation_device):
        self.filename = filename
        self.translation = translation
        self.cyrillic_transcription = cyrillic_transcription
        self.latin_transcription = latin_transcription
        self.annotation_form = annotation_form
        self.annotation_indexation = annotation_indexation
        self.annotation_device = annotation_device

    @classmethod
    def from_tg_file(cls, filepath, translation_name, cyrillic_transcription_name, latin_transcription_name,
                     annotation_form_name, annotation_indexation_name, annotation_device_name):
        tg = textgrid.openTextgrid(filepath, includeEmptyIntervals=True)

        translation, cyrillic_transcription, \
            latin_transcription, annotation_form, \
            annotation_indexation, annotation_device = \
            tg.tierDict[translation_name], \
                tg.tierDict[cyrillic_transcription_name], \
                tg.tierDict[latin_transcription_name], \
                tg.tierDict[annotation_form_name], \
                tg.tierDict[annotation_indexation_name], \
                tg.tierDict[annotation_device_name]

        return GridText(filepath, translation, cyrillic_transcription, latin_transcription,
                        annotation_form, annotation_indexation, annotation_device)

    @classmethod
    def get_labels(cls, layer):
        entries = layer.entryList
        labels = [label for _, _, label in entries]

        return labels

    def get_reference_tracking_devices(self):  # shitty code

        sentence_transcription_entries = self.latin_transcription.entryList
        sentence_translation_entries = self.translation.entryList
        annotation_form_entries = self.annotation_form.entryList
        annotation_indexation_entries = self.annotation_indexation.entryList
        annotation_device_entries = self.annotation_device.entryList
        sentence_id = 0

        devices = []

        if len(annotation_form_entries) != len(annotation_indexation_entries) != len(annotation_device_entries):
            raise IndexError("Annotation tiers differ in length!")

        if len(sentence_transcription_entries) != len(sentence_translation_entries):
            raise IndexError("Sentence tiers differ in length!")
        sentences = [Sentence(sentence_transcription_entries[ind][2], sentence_translation_entries[ind][2])
                     for ind in range(len(sentence_transcription_entries))]

        device_id = 0
        for start_device, end_device, label_device in annotation_form_entries:
            if annotation_indexation_entries[device_id][2] in ('pred', ''):
                device_id += 1
                continue
            while True:
                start_sentence, end_sentence, label_sentence = sentence_transcription_entries[sentence_id]
                _, _, label_sentence_translation = sentence_translation_entries[sentence_id]

                if (start_sentence <= start_device < end_sentence):
                    break
                sentence_id += 1

            if label_device not in label_sentence and label_device != 'Ø':
                print(label_device, ':', label_sentence)
                raise IndexError("Device is not found")

            if label_device == 'Ø':
                label_device = annotation_form_entries[device_id - 1][2]

            reference_tracking_device = ReferenceTrackingDevice(label_device,
                                                                annotation_indexation_entries[device_id][2],
                                                                annotation_device_entries[device_id][2],
                                                                start_device,
                                                                end_device,
                                                                Sentence(label_sentence, label_sentence_translation))

            devices.append(reference_tracking_device)
            device_id += 1
        return devices, sentences

def calculate_distance(reference_tracking_devices, sentences):
    ad_list = []

    for tracking_device_id, tracking_device in enumerate(reference_tracking_devices):
        if not tracking_device.device.startswith(('PROX', 'MED', 'DIST', 'SELF')):
            continue
        previous_referring_id = tracking_device_id - 1
        ad = len(tracking_device.source_sentence.transcription[:tracking_device.source_sentence.transcription.find(tracking_device.form)].split())
        while previous_referring_id != -1:
            previous_referring = reference_tracking_devices[previous_referring_id]
            sentence_transcription = previous_referring.source_sentence.transcription
            if tracking_device.referent == previous_referring.referent:
                ad += len(sentence_transcription[sentence_transcription.find(previous_referring.form):].split())
                sentences_transcriptions = [sent.transcription for sent in sentences]
                ad += len(' '.join(sentences_transcriptions[sentences_transcriptions.index(sentence_transcription) + 1:sentences_transcriptions.index(tracking_device.source_sentence.transcription)]).split())
                ad_seconds = tracking_device.start - previous_referring.end
                print(tracking_device.form, previous_referring.form, ad, ad_seconds)
                ad_list.append((tracking_device, previous_referring, ad, ad_seconds))
                break
            previous_referring_id -= 1
        else:
            IndexError("Previous referring is not found")

    return ad_list

def auto_annotation(data_list):
    auto_annotated_data_list = []
    for tracking_device, previous_referring, ad, ad_seconds in data_list:
        if '_NP' in tracking_device.device:
            syntactic_position = 'ADNOM'
        else:
            syntactic_position = 'INDEP'

        if 'PROX' in tracking_device.device:
            demonstrative_type = 'PROX'
        elif 'MED' in tracking_device.device:
            demonstrative_type = 'MED'
        elif 'DIST' in tracking_device.device:
            demonstrative_type = 'DIST'
        elif 'SELF' in tracking_device.device:
            demonstrative_type = 'SELF'
        else:
            raise NameError("Type is not found!")

        if tracking_device.referent in ('man', 'man2', 'boys', 'boy', 'girl', 'goat'):
            animacy = 'ANIM'
        else:
            animacy = 'INANIM'
        auto_annotated_data_list.append((tracking_device, previous_referring,
                                        ad, ad_seconds, syntactic_position, demonstrative_type, animacy))

    return auto_annotated_data_list
def write_ad_values(data_list, filename):
    with open('ad_values.csv', 'a', encoding='utf-8') as f:
        for tracking_device, previous_referring, ad, ad_seconds, syntactic_position, demonstrative_type, animacy \
                in data_list:
            f.write('\t'.join([str(ad), str(ad_seconds), demonstrative_type, syntactic_position, animacy,
                               tracking_device.device, tracking_device.form, tracking_device.referent,
                               str(tracking_device.start), str(tracking_device.end), tracking_device.source_sentence.transcription,
                               tracking_device.source_sentence.translation,
                               previous_referring.device, previous_referring.form, previous_referring.referent,
                               str(previous_referring.start), str(previous_referring.end),
                               previous_referring.source_sentence.transcription,
                               previous_referring.source_sentence.translation,
                               filename
                               ]) + '\n')

def main():
    with open('ad_values.csv', 'w', encoding='utf-8') as f:
        f.write('\t'.join(['ad', 'ad_seconds', 'dem', 'synt_pos', 'anim',
                           'anaphor_device', 'anaphor_form', 'anaphor_referent',
                           'anaphor_start', 'anaphor_end', 'anaphor_sentence_transcription',
                           'anaphor_sentence_translation',
                           'previous_device', 'previous_form', 'previous_referent',
                           'previous_start', 'previous_end',
                           'previous_sentence_transcription',
                           'previous_sentence_translation',
                           'filename']) + '\n')

    tier_names = ['translation', 'transcription_cyr', 'transcription_lat',
                  'annotation_form', 'annotation_indexation', 'annotation_device']

    for root, dirs, files in walk('annotated_textgrids'):
        for filename in files:
            path_to_tg = join('annotated_textgrids', filename)
            tg = GridText.from_tg_file(path_to_tg, *tier_names)
            reference_tracking_devices, sentences = tg.get_reference_tracking_devices()
            write_ad_values(auto_annotation(calculate_distance(reference_tracking_devices, sentences)), filename)

if __name__ == '__main__':
    main()

