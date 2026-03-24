Feature: Login
  Background:
    Given the application is running

  @test
  Scenario: Successful login
    When I enter "admin" in the username field
    Then I should see the dashboard
