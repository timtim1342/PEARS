from main import GridText
from os.path import join
from os import walk
from re import findall
def auto_annotation_light(data_list):

    auto_annotated_data_list = []

    for tracking_device in data_list:
        if '_NP' in tracking_device.device:
            syntactic_position = 'ADNOM'
        else:
            syntactic_position = 'INDEP'

        distance_found = findall(r'PROX|MED|DIST|GA|GO|HA', tracking_device.device)
        elevation_found = findall(r'ABOVE|BELOW|LEVEL', tracking_device.device)

        if any(distance_found):
            distance_contrast = distance_found[0]
        else:
            distance_contrast = 'NA'

        if any(elevation_found):
            elevation = elevation_found[0]
        else:
            elevation = 'NA'

        if tracking_device.referent in ('man', 'man2', 'boys', 'boy', 'boy1', 'girl', 'goat'):
            animacy = 'ANIM'
        else:
            animacy = 'INANIM'
        if tracking_device.referent in ('man', 'boys', 'boy'):
            protagonist = 'protagonist'
        else:
            protagonist = 'secondary character'

        auto_annotated_data_list.append((tracking_device, syntactic_position, distance_contrast, elevation, animacy, protagonist))
    return auto_annotated_data_list


def write_ad_values_light(data_list, filename, text_length):
    lang = filename.split('_')[0]
    with open('extracted_demonstrartives.csv', 'a', encoding='utf-8') as f:
        for tracking_device, syntactic_position, distance_contrast, elevation, animacy, protagonist \
                in data_list:
            f.write('\t'.join([lang,
                               distance_contrast, elevation, syntactic_position, animacy, protagonist,
                               tracking_device.device, tracking_device.form, tracking_device.referent,
                               str(tracking_device.start), str(tracking_device.end),
                               tracking_device.source_sentence.transcription,
                               tracking_device.source_sentence.translation,
                               filename,
                               text_length]) + '\n')

def main():
    with open('extracted_demonstrartives.csv', 'w', encoding='utf-8') as f:
        f.write('\t'.join(['lang',
                           'distance_contrast', 'elevation', 'synt_pos', 'anim', 'role',
                           'anaphor_device', 'anaphor_form', 'anaphor_referent',
                           'anaphor_start', 'anaphor_end',
                           'anaphor_sentence_transcription',
                           'anaphor_sentence_translation',
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
                write_ad_values_light(auto_annotation_light(reference_tracking_devices), filename, text_length)
            except Exception as ex:
                print(filename, str(ex))
                break



if __name__ == '__main__':
    main()