from praatio import textgrid
from os.path import join
from os import walk


class Sentence:
    def __init__(self, transcription, translation):
        self.transcription = transcription
        self.translation = translation


class ReferenceTrackingDevice:
    def __init__(self, form, referent, device, start, end, source_sentence, mention=None):
        self.form = form
        self.referent = referent
        self.device = device
        self.start = start
        self.end = end
        self.source_sentence = source_sentence
        self.mention = mention


class GridText:
    def __init__(self, filename, translation, cyrillic_transcription, latin_transcription,
                 annotation_form, annotation_indexation, annotation_device, annotation_mention):
        self.filename = filename
        self.translation = translation
        self.cyrillic_transcription = cyrillic_transcription
        self.latin_transcription = latin_transcription
        self.annotation_form = annotation_form
        self.annotation_indexation = annotation_indexation
        self.annotation_device = annotation_device
        self.annotation_mention = annotation_mention

    @classmethod
    def from_tg_file(cls, filepath, translation_name, cyrillic_transcription_name, latin_transcription_name,
                     annotation_form_name, annotation_indexation_name, annotation_device_name, annotation_mention_name):
        tg = textgrid.openTextgrid(filepath, includeEmptyIntervals=True)

        translation, cyrillic_transcription, \
            latin_transcription, annotation_form, \
            annotation_indexation, annotation_device, annotation_mention = \
            tg.tierDict[translation_name], \
                tg.tierDict[cyrillic_transcription_name], \
                tg.tierDict[latin_transcription_name], \
                tg.tierDict[annotation_form_name], \
                tg.tierDict[annotation_indexation_name], \
                tg.tierDict[annotation_device_name], \
                tg.tierDict[annotation_mention_name]

        return GridText(filepath, translation, cyrillic_transcription, latin_transcription,
                        annotation_form, annotation_indexation, annotation_device, annotation_mention)

    def get_reference_tracking_devices(self):  # shitty code

        sentence_transcription_entries = self.latin_transcription.entryList
        sentence_translation_entries = self.translation.entryList
        annotation_form_entries = self.annotation_form.entryList
        annotation_indexation_entries = self.annotation_indexation.entryList
        annotation_device_entries = self.annotation_device.entryList
        annotation_mention_entries = self.annotation_mention.entryList
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
            label_device = label_device.replace('?', '')
            if annotation_indexation_entries[device_id][2] in ('pred', ''):
                device_id += 1
                continue
            while True:
                start_sentence, end_sentence, label_sentence = sentence_transcription_entries[sentence_id]
                _, _, label_sentence_translation = sentence_translation_entries[sentence_id]
                if (start_sentence <= start_device and start_device < end_sentence):
                    break
                sentence_id += 1

            if label_device.lower() not in label_sentence.lower() and label_device != 'Ø':
                print(start_device, label_device, ':', label_sentence)
                raise IndexError("Device is not found")

            if label_device == 'Ø':
                label_device = annotation_form_entries[device_id - 1][2]

            mention = '>1'
            for start_mention, end_mention, label_mention in annotation_mention_entries:
                if start_mention == start_device and end_mention == end_device and label_mention == '1':
                    mention = '1'
                    break

            reference_tracking_device = ReferenceTrackingDevice(label_device,
                                                                annotation_indexation_entries[device_id][2],
                                                                annotation_device_entries[device_id][2],
                                                                start_device,
                                                                end_device,
                                                                Sentence(label_sentence, label_sentence_translation),
                                                                mention)

            devices.append(reference_tracking_device)
            device_id += 1
        return devices, sentences

    def get_text_length_words(self):
        entries = self.latin_transcription.entryList
        text_length = len(' '.join([label for _, _, label in entries]).split())

        return text_length

def calculate_distance(reference_tracking_devices, sentences):
    ad_list = []

    for tracking_id, tracking_device in enumerate(reference_tracking_devices):
        if not tracking_device.device.startswith(('PROX', 'MED', 'DIST', 'ABOVE', 'BELOW')):
            continue

        previous_id = tracking_id - 1
        tracking_source_transcription = tracking_device.source_sentence.transcription
        tracking_form = tracking_device.form
        tracking_referent = tracking_device.referent
        tracking_start = tracking_device.start
        tracking_position = tracking_source_transcription.find(tracking_form)
        len_tracking_device_sentence = len(tracking_source_transcription[:tracking_position].split())
        ad = len_tracking_device_sentence

        while previous_id != -1:
            previous_referring = reference_tracking_devices[previous_id]
            previous_source_transcription = previous_referring.source_sentence.transcription
            previous_referent = previous_referring.referent
            previous_form = previous_referring.form
            previous_end = previous_referring.end
            previous_position = previous_source_transcription.find(previous_form)

            if tracking_referent == previous_referent:
                ad += len(previous_source_transcription[previous_position:].split())
                sentences_transcriptions = [sent.transcription for sent in sentences if sent.transcription != '']
                between_sentences_transcription = sentences_transcriptions[sentences_transcriptions.index(previous_source_transcription) + 1:sentences_transcriptions.index(tracking_source_transcription)]
                ad += len(' '.join(between_sentences_transcription).split())
                ad_clauses = len(between_sentences_transcription) + 1
                if previous_source_transcription == tracking_source_transcription:
                    ad = len(previous_source_transcription[previous_position:tracking_position].split())
                    ad_clauses = 0
                ad_seconds = tracking_start - previous_end

                wad = ad
                wad_clauses = ad_clauses
                if previous_referring.device != 'ZERO':
                    wad_seconds = ad_seconds
                    explicit_referring = previous_referring
                else:
                    previous_id -= 1
                    while previous_id != -1:
                        explicit_referring = reference_tracking_devices[previous_id]
                        explicit_source_transcription = explicit_referring.source_sentence.transcription
                        explicit_referent = explicit_referring.referent
                        explicit_form = explicit_referring.form
                        explicit_device = explicit_referring.device
                        explicit_end = explicit_referring.end
                        explicit_position = explicit_source_transcription.find(explicit_form)

                        if tracking_referent == explicit_referent and explicit_device != 'ZERO':
                            wad += len(explicit_source_transcription[explicit_position:].split())
                            wad += len(previous_source_transcription[:previous_position].split())
                            between_sentences_transcription_wad = sentences_transcriptions[sentences_transcriptions.index(explicit_source_transcription) + 1:sentences_transcriptions.index(previous_source_transcription)]
                            wad += len(' '.join(between_sentences_transcription_wad).split())
                            wad_clauses += len(between_sentences_transcription_wad) + 1
                            if explicit_source_transcription == previous_source_transcription:
                                wad = len(explicit_source_transcription[explicit_position:previous_position].split()) + ad
                                wad_clauses = 0
                            wad_seconds = tracking_start - explicit_end

                            break
                        previous_id -= 1
                    else:
                        raise IndexError(f"Previous explicit referring is not found {tracking_device.form, tracking_start}")

                print(tracking_device.form, previous_referring.form, explicit_referring.form, ad, ad_seconds, ad_clauses, wad, wad_seconds, wad_clauses)
                ad_list.append((tracking_device, previous_referring, explicit_referring, ad, ad_seconds, ad_clauses, wad, wad_seconds, wad_clauses))
                break
            previous_id -= 1
        else:
            raise IndexError(f"Previous referring is not found {tracking_device.form, tracking_start}")

    return ad_list

def auto_annotation(data_list):
    auto_annotated_data_list = []
    for tracking_device, previous_referring, previous_explicit_referring, ad, ad_seconds, ad_clauses, wad, wad_seconds, wad_clauses in data_list:
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
        elif 'ABOVE' in tracking_device.device:
            demonstrative_type = 'ABOVE'
        elif 'BELOW' in tracking_device.device:
            demonstrative_type = 'BELOW'
        else:
            raise NameError("Type is not found!")

        if tracking_device.referent in ('man', 'man2', 'boys', 'boy', 'boy1', 'girl', 'goat'):
            animacy = 'ANIM'
        else:
            animacy = 'INANIM'
        if tracking_device.referent in ('man', 'boys', 'boy'):
            protagonist = 'protagonist'
        else:
            protagonist = 'secondary character'
        auto_annotated_data_list.append((tracking_device, previous_referring, previous_explicit_referring,
                                        ad, ad_seconds, ad_clauses, wad, wad_seconds, wad_clauses, syntactic_position, demonstrative_type, animacy, protagonist))

    return auto_annotated_data_list
def write_ad_values(data_list, filename, text_length):
    lang = filename.split('_')[0]
    with open('ad_values.csv', 'a', encoding='utf-8') as f:
        for tracking_device, previous_referring, previous_explicit_referring, ad, ad_seconds, ad_clauses, wad, wad_seconds, wad_clauses, syntactic_position, demonstrative_type, animacy, protagonist \
                in data_list:
            f.write('\t'.join([lang, str(ad), str(ad_seconds), str(ad_clauses), str(wad), str(wad_seconds), str(wad_clauses),
                               demonstrative_type, syntactic_position, animacy, protagonist,
                               tracking_device.device, tracking_device.form, tracking_device.referent,
                               str(tracking_device.start), str(tracking_device.end),
                               tracking_device.source_sentence.transcription,
                               tracking_device.source_sentence.translation,
                               previous_referring.device, previous_referring.form, previous_referring.referent,
                               str(previous_referring.start), str(previous_referring.end),
                               previous_referring.mention,
                               previous_referring.source_sentence.transcription,
                               previous_referring.source_sentence.translation,
                               previous_explicit_referring.device, previous_explicit_referring.form, previous_explicit_referring.referent,
                               str(previous_explicit_referring.start), str(previous_explicit_referring.end),
                               previous_explicit_referring.mention,
                               previous_explicit_referring.source_sentence.transcription,
                               previous_explicit_referring.source_sentence.translation,
                               filename,
                               text_length]) + '\n')
def main():
    with open('ad_values.csv', 'w', encoding='utf-8') as f:
        f.write('\t'.join(['lang', 'ad', 'ad_seconds', 'ad_clauses', 'wad', 'wad_seconds', 'wad_clauses',
                           'dem', 'synt_pos', 'anim', 'role',
                           'anaphor_device', 'anaphor_form', 'anaphor_referent',
                           'anaphor_start', 'anaphor_end',
                           'anaphor_sentence_transcription',
                           'anaphor_sentence_translation',
                           'previous_device', 'previous_form', 'previous_referent',
                           'previous_start', 'previous_end',
                           'previous_mention',
                           'previous_sentence_transcription',
                           'previous_sentence_translation',
                           'previous_explicit_device', 'previous_explicit_form', 'previous_explicit_referent',
                           'previous_explicit_start', 'previous_explicit_end',
                           'previous_explicit_mention',
                           'previous_explicit_sentence_transcription',
                           'previous_explicit_sentence_translation',
                           'filename',
                           'length_words']) + '\n')

    tier_names = ['translation', 'transcription_cyr', 'transcription_lat',
                  'annotation_form', 'annotation_indexation', 'annotation_device', 'annotation_mention']

    for root, dirs, files in walk('annotated_textgrids'):
        for filename in files:
            # if filename.startswith('mhb_'):  # only for kina rutul
            #     continue  # only for kina rutul
            path_to_tg = join('annotated_textgrids', filename)
            tg = GridText.from_tg_file(path_to_tg, *tier_names)
            text_length = str(tg.get_text_length_words())
            try:
                reference_tracking_devices, sentences = tg.get_reference_tracking_devices()
            except Exception as ex:
                print(filename, str(ex))
                break

            try:
                write_ad_values(auto_annotation(calculate_distance(reference_tracking_devices, sentences)), filename, text_length)
            except Exception as ex:
                print(filename, str(ex))
                break



if __name__ == '__main__':
    main()

