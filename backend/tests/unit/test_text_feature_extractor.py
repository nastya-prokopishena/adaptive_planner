import numpy as np

from backend.infrastructure.ml.text_feature_extractor import TextFeatureExtractor


def test_fit_stores_input_metadata():
    extractor = TextFeatureExtractor()

    result = extractor.fit(["a", "b"], y=[1, 2])

    assert result is extractor
    assert extractor._fit_input_count == 2
    assert extractor._fit_has_target is True


def test_transform_returns_expected_shape_and_counts():
    extractor = TextFeatureExtractor()

    features = extractor.transform(
        [
            "1. реалізувати backend api? - описати результат",
            "прочитати матеріал",
        ]
    )

    assert isinstance(features, np.ndarray)
    assert features.shape == (2, 7)

    first = features[0]

    assert first[0] > 0
    assert first[2] >= 1
    assert first[3] >= 1
    assert first[4] == 1
    assert first[5] >= 1
    assert first[6] == 1
