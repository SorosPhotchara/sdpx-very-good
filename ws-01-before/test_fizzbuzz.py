from fizzbuzz import fizzbuzz


def test_fizzbuzz_sequence_through_fifteen():
    assert fizzbuzz(15) == [
        "1",
        "2",
        "Fizz",
        "4",
        "Buzz",
        "Fizz",
        "7",
        "8",
        "Fizz",
        "Buzz",
        "11",
        "Fizz",
        "13",
        "14",
        "FizzBuzz",
    ]


def test_fizzbuzz_zero_returns_empty_sequence():
    assert fizzbuzz(0) == []


def test_fizzbuzz_preserves_numbers_after_fifteen():
    result = fizzbuzz(16)
    assert result[-1] == "16"
    assert len(result) == 16
